# Question Types & Format

A poll is defined by a questions file passed to `quorumcall add-poll` or the
`POST /api/polls` endpoint. Both **JSON** and **TOML** are accepted; the format
is chosen by file extension (`.json` / `.toml`).

## JSON Format

```json
{
  "questions": [
    {
      "id": "q1",
      "type": "radio",
      "title": "Are you satisfied with your experience?",
      "required": true,
      "options": ["Yes", "No", "Somewhat"],
      "next": { "Yes": "q3", "No": "q2", "Somewhat": "q2" }
    },
    {
      "id": "q2",
      "type": "long_answer",
      "title": "What could be improved?",
      "next": "q3"
    },
    {
      "id": "q3",
      "type": "rating",
      "title": "Rate your overall experience",
      "required": true,
      "rating_max": 5
    }
  ]
}
```

## TOML Format

```toml
[[questions]]
id = "q1"
type = "radio"
title = "Are you satisfied with your experience?"
required = true
options = ["Yes", "No", "Somewhat"]

[questions.next]
Yes = "q3"
No = "q2"
Somewhat = "q2"

[[questions]]
id = "q2"
type = "long_answer"
title = "What could be improved?"
next = "q3"

[[questions]]
id = "q3"
type = "rating"
title = "Rate your overall experience"
required = true
rating_max = 5
```

## Common Fields

Every question accepts:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique question identifier, referenced by `next` |
| `type` | yes | One of the [supported types](#supported-types) |
| `title` | yes | The question text shown to respondents |
| `description` | no | Helper text shown below the title |
| `required` | no | Boolean, default `false` |
| `next` | no | [Conditional branching](#conditional-branching) target |

## Conditional Branching

The `next` field controls which question a respondent sees after answering.

| Value | Behaviour |
|-------|-----------|
| omitted / `null` | Next question in order; submit if it is the last |
| `"q5"` | Always jump to `q5` |
| `{"Yes": "q3", "No": "q2"}` | Route by the selected answer; falls back to the next question in order if the answer is not mapped |

The browser UI evaluates this in JavaScript (`nextId()` in `ui.py`); the server
stores whatever answers it receives.

## Supported Types

| Type | Description | Extra fields |
|------|-------------|--------------|
| `short_answer` | Single-line text | — |
| `long_answer` | Multi-line textarea | — |
| `number` | Numeric input | — |
| `email` | Email input | — |
| `phone` | Telephone input | — |
| `url` | URL input | — |
| `date` | Date picker | — |
| `time` | Time picker | — |
| `datetime` | Date + time picker | — |
| `radio` | Single choice | `options`, `include_other` |
| `checkbox` | Multiple choice | `options`, `include_other` |
| `dropdown` | Select menu | `options` |
| `true_false` | Yes / No (or custom labels) | `options` |
| `slider` | Range slider | `slider_min`, `slider_max`, `slider_step`, `slider_labels` |
| `rating` | 1–N star/number rating | `rating_max` |
| `likert` | Agreement scale | `likert_options` |

`include_other: true` on a `radio` or `checkbox` question adds a free-text
"Other…" option. Values submitted through it are stored prefixed with `Other: `
and surfaced separately in [results](api.md#results-shape) under `other_values`.
