# Evaluation Rubric

Scores are assigned per answer and per dimension.

## Overall Score

```text
0 = wrong or hallucinated
1 = partially correct but missing key source/condition
2 = correct answer with weak citation or minor omission
3 = correct, cited, version-safe, condition/exception-safe
```

## Dimension Checklist

- Retrieval recall: required document/provision found.
- Citation accuracy: citation points to correct source and locator.
- Version safety: no replaced/draft/current confusion.
- Condition handling: applicability conditions preserved.
- Exception handling: exclusions preserved.
- Uncertainty handling: says unknown when evidence is insufficient.
- Concision: answer is not padded with irrelevant context.

## Automatic Failure Labels

```text
missed_document
missed_provision
wrong_version
unsupported_answer
citation_missing
citation_wrong
exception_dropped
condition_dropped
date_confusion
overconfident_unknown
```
