# Marketplace Activity

A software development company wants to identify which employees are delaying work due to overload or poor performance.

Employees can:
- assign tasks
- perform tasks
- perform code/task reviews
- perform deployments
- provide approvals
- participate in meetings
- send messages
Work hours are from 9:00 to 17:00 UTC.

Employees are in different projects, have different roles (junior, mid, senior, manager), and, depending on their role, have different responsibilities. These responsibilities are not clearly assigned; for example, a mid can both work on a task and perform code reviews, but they have fewer meetings than seniors and managers. Everyone above a junior reviews/approves tasks/deployments to employees below them (mid to junior, etc.). Some employees are overloaded with work (tasks, meetings, messages, etc.) or simply have poor performance, causing blocks or significant delays of the entire work pipeline for tasks they are assigned to. Your goal is to identify these employees.

Dataset:

- The generated CSV files are available directly in `/app`.

Answer format:

- Write your final answer to `/app/answer.json`.
- The file must contain only a JSON object with indices of the bottleneck employees

Example:

```json
{"answer":[1,2,3]}
```
