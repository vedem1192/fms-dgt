# Standard
from dataclasses import dataclass
from functools import partial
from typing import Any, Iterable, List, Optional, Union

# Local
from fms_dgt.base.registry import register_block
from fms_dgt.blocks.validators import BaseValidatorBlock, BaseValidatorBlockData

try:
    # Third Party
    from rouge_score import rouge_scorer
except ModuleNotFoundError:
    pass


@dataclass(kw_only=True)
class RougeDedupData(BaseValidatorBlockData):
    input: str


@register_block("rouge_scorer")
class RougeDedupValidator(BaseValidatorBlock):
    """Base Class for all Validators"""

    DATA_TYPE: RougeDedupData = RougeDedupData

    def __init__(self, threshold: float = 1.1, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if threshold is None:
            # if threshold is set to None, we'll put it as an unreachably high value
            threshold = 1.1

        self._threshold = threshold

        self._cache = dict()

        self.scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=False)

    def tokenize(self, inp: Union[List, str]):
        if type(inp) == list:
            return [self.tokenize(el) for el in inp]
        else:
            if inp not in self._cache:
                self._cache[inp] = self.scorer._tokenizer.tokenize(inp)
            return self._cache[inp]

    def execute(
        self,
        inputs: Iterable[RougeDedupData],
        *,
        context: Optional[List[str]] = None,
    ):
        """Deduplicator that removes elements of `inputs` that are too rouge-similar. By default it will pick the one that is maximally dissimilar from `context` to keep"""

        # tokenize context
        context = self.tokenize(context) if context else []

        tokenized = []
        for inp in inputs:
            # TODO: Safety check this
            tokenized.append((self.tokenize(inp.input), inp))

        # first score inputs by rouge similarity to context
        ranked_inputs = []
        for new_tokens, inp in tokenized:
            worst_rouge_score = (
                max(
                    map(
                        partial(rouge_scorer._score_lcs, new_tokens),
                        context,
                    ),
                    key=lambda x: x.fmeasure,
                ).fmeasure
                if context and self._threshold <= 1
                else -1
            )

            is_valid_wrt_context = worst_rouge_score < self._threshold
            if is_valid_wrt_context or not self._filter_invalids:
                ranked_inputs.append(
                    (
                        worst_rouge_score,
                        is_valid_wrt_context,
                        new_tokens,
                        inp,
                    )
                )

        ranked_inputs.sort(key=lambda x: x[0])

        # now add
        all_tokens = []
        for _, _, new_tokens, inp in ranked_inputs:
            all_tokens.append(new_tokens)

        outputs, to_save = [], []
        for i, (_, is_valid_wrt_context, new_tokens, inp) in enumerate(ranked_inputs):
            # only check against elements we've already added
            check_against = all_tokens[:i]
            inp.is_valid = (
                self._validate(new_tokens, check_against) and is_valid_wrt_context
            )
            if inp.is_valid or not self._filter_invalids:
                outputs.append(inp)

            if not inp.is_valid:
                to_save.append(inp)

        self.save_data(to_save)

        return outputs

    def _validate(self, new_tokens: List[int], check_tokens: List[List[int]]) -> bool:
        """Runs through all the validators if data list is None. Otherwise just runs through the validators specified for data in the List"""

        if (
            self._threshold > 1
        ):  # if threshold greater than 1, no need to bother computing this
            return True

        if len(check_tokens) == 0:
            return True

        rouge_scores = map(
            partial(rouge_scorer._score_lcs, new_tokens),
            check_tokens,
        )

        return max(rouge_scores, key=lambda x: x.fmeasure).fmeasure < self._threshold
