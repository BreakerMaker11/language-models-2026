# Course Feedback Fixes — Issue Tracker

**Branch**: `course_feedback_fixes`
**Reference repo**: `/Users/mo/Desktop/Home/AILab/ProjectWorkspace/LLMFCourse/`
**Last updated**: 2026-05-22

---

## Status Legend

| Status | Meaning |
|--------|---------|
| OPEN | Identified, not yet started |
| IN PROGRESS | Currently being worked on |
| FIXED | Fix applied and verified |
| WONT FIX | Acknowledged but not changing |

---

## Issues

| # | Area | Issue | Description | Status | Fix Summary |
|---|------|-------|-------------|--------|-------------|
| 1 | Notebook W1 | Typo in Use Case 2: Decision-Making | "vegeteraion" should be "vegetarian" | FIXED | Corrected spelling in week1_introduction_to_llms.ipynb |
| 2 | Docs | CLAUDE.md and project_structure.md reference wrong spec folder | Says specs go in `prompts/` but skill saves to `specs/`. Also `project_structure.md` described `prompts/` as where to save YAML specs — corrected to clarify it holds prompt markdown files only. | FIXED | Updated `CLAUDE.md` line 42, `project_structure.md` lines 60 and 92 to reference `specs/` correctly |

---

## Change Log

| Date | Issue # | Files Changed | Summary |
|------|---------|---------------|---------|
| 2026-05-22 | 1 | notebooks/week1_introduction_to_llms.ipynb | Fixed "vegeteraion" → "vegetarian" |
| 2026-05-22 | 2 | CLAUDE.md, project_structure.md | Changed spec folder references from `prompts/` to `specs/`; corrected `prompts/` folder description |
