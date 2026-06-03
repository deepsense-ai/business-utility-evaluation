# Bottleneck Employees

## Description

This scenario models a software company where employees collaborate on projects, move work through delivery pipelines, and produce operational records such as task assignments, task events, code reviews, QA tests, approvals, deployments, incidents, meetings, and messages.

The analytical target is to identify hidden bottleneck employees from the public CSV files. Bottleneck employees are not labeled in the exported tables. Their effect is visible through delayed work, unusually high routing through coordination-heavy activities, slow reviews or approvals, heavy meeting/message load, and pipelines that take longer when they are involved.

## Task Design

### Difficulty and Signal Strength

The task difficulty is mostly controlled by the size and visibility of the bottleneck effects.

Important knobs include:

- `CONFIG["bottlenecks"]["n_bottleneck_employees"]`
- `CONFIG["bottlenecks"]["seniority_selection_weights"]`
- `CONFIG["bottlenecks"]["reason_weights"]`
- `CONFIG["bottlenecks"]["overload_response_multiplier_range"]`
- `CONFIG["bottlenecks"]["underperformance_speed_multiplier_range"]`
- `CONFIG["bottlenecks"]["routing_multiplier_range"]`
- `CONFIG["bottlenecks"]["meeting_multiplier_range"]`
- `CONFIG["bottlenecks"]["message_multiplier_range"]`
- `CONFIG["activity"]["base_meetings_per_weekday"]`
- `CONFIG["activity"]["base_messages_per_weekday"]`
- `CONFIG["pipelines"]["pipeline_mix"]`

Tests show that the share of overloaded bottleneck employees, controlled by `CONFIG["bottlenecks"]["reason_weights"]`, is a very important parameter, as the models (at least in the current setup) do well in finding the underperforming employees, but struggle to find the overloaded ones. Therefore, increasing the share of purely overloaded employees makes the task more difficult.

Increasing bottleneck multipliers makes bottleneck employees easier to detect. Reducing the multipliers makes the task harder and forces analysis to rely on weaker aggregate patterns.

More meetings and messages make overload easier to see, but they can also add noise. More large-feature and approval-heavy pipelines increase the importance of senior and manager bottlenecks.

For more details about the parameters see the sections below.

## Generation

### Local Generation

From the repository root:

```bash
uv run python harbor/tasks/bottleneck_employees/environment/generate.py
```

It will produce the output files in the repository root. The output directory can be set with the `BOTTLENECK_EMPLOYEES_OUTPUT_DIR` variable.

The generator uses `numpy` and `pandas`. Generation is deterministic for a fixed `CONFIG["seed"]` and RNG configuration.

Managed CSV outputs are rewritten when `CONFIG["output"]["cleanup_outputs"] = True`.

### Generated Outputs

Only the domain tables from the task schema are written as public CSV files:

- `employee_*.csv`
- `project_*.csv`
- `task_*.csv`
- `task_assignment_*.csv`
- `task_event_*.csv`
- `code_review_*.csv`
- `qa_test_*.csv`
- `deployment_*.csv`
- `incident_*.csv`
- `approval_*.csv`
- `meeting_*.csv`
- `meeting_participant_*.csv`
- `message_metadata_*.csv`
- `task_dependency_*.csv`

Files are split into indexed chunks according to `CONFIG["output"]["rows_per_file"]`.

The generator can also write a human-readable `simulation_output.txt` when `CONFIG["output"]["write_simulation_output"] = True`. This file is intended for debugging and auditing the simulator. It includes aggregated row counts and a detailed section describing the hidden bottleneck employees, their hidden profile values, and their generated activity. Those hidden details are not exported to the public CSV files.

## Data Model

### Public Schema

The public dataset follows the schema:

- `EMPLOYEE`: public employee metadata, including role, seniority, department, manager, and hire date
- `PROJECT`: project name, business domain, and priority level
- `TASK`: work item metadata, including project, task type, priority, status, complexity, risk, creation time, and completion time
- `TASK_ASSIGNMENT`: employee assignment intervals and assignment roles
- `TASK_EVENT`: timestamped events performed by employees on tasks
- `CODE_REVIEW`: review records linking reviewer, author, review outcome, change count, and review timing
- `QA_TEST`: testing records linking tester, result, bug count, and test time
- `DEPLOYMENT`: deployment records, deployment type, approver, rollback flag, and deployment time
- `INCIDENT`: incident records linked to tasks and owners
- `APPROVAL`: approval records with approver, approval type, result, and timing
- `MEETING`: meeting records with organizer and time window
- `MEETING_PARTICIPANT`: meeting attendance links
- `MESSAGE_METADATA`: sender/receiver communication metadata
- `TASK_DEPENDENCY`: dependencies between blocking and blocked tasks

Timestamp fields are rounded to full seconds. Floating point values exported to CSV are rounded according to `CONFIG["output"]["float_rounding"]`.

### Hidden Data

The simulator maintains private employee parameters that influence behavior but are not exported in `employee_*.csv`:

- `skill_score`
- `review_capacity`
- `deployment_authority`
- `speed_multiplier`
- `response_multiplier`
- `routing_multiplier`
- `meeting_multiplier`
- `message_multiplier`
- `bottleneck_reason`
- project membership used for internal routing
- bottleneck label

These hidden fields are used to produce realistic public behavior.

The hidden answer key is controlled by:

- `CONFIG["output"]["write_answer_file"]`
- `CONFIG["output"]["answer_path"]`
- `BOTTLENECK_EMPLOYEES_ANSWER_PATH`

## Simulation Mechanics

### Simulation Setup

Global behavior is controlled by the top-level `CONFIG` in `environment/generate.py`.

The main sections are:

- `scale`: number of employees, number of projects, task volume, and minimum daily task creation
- `calendar`: working hours and time handling
- `organization`: seniority mix, department mix, project membership, hire-date ranges, and hidden skill distributions
- `projects`: business domains, synthetic project names, and project priority distribution
- `bottlenecks`: number of bottleneck employees, bottleneck seniority selection weights, reason weights, and multiplier ranges
- `activity`: weekday effects, meetings, messages, handoff messages, and communication channel mix
- `pipelines`: pipeline mix, task priority distributions, complexity/risk ranges, optional QA/review behavior, and large-feature decomposition settings
- `action_model`: action durations, response delays, priority effects, rollback probabilities, and risk/complexity effects
- `actor_selection`: role-specific routing weights used to select employees for different actions
- `output`: file splitting, answer generation, float rounding, cleanup, and optional simulation trace

### Employees

Employees are generated as agents. Each employee has public attributes and hidden behavioral parameters.

Public attributes include:

- `employee_id`
- `role`
- `seniority_level`
- `department`
- `manager_id`
- `hire_date`

Seniority affects likely duties but does not make duties deterministic. For example, managers are more likely to organize meetings and resolve approvals, seniors are more likely to review and approve work, mids and juniors are more likely to implement tasks, and QA/SRE/security departments influence testing, deployment, and review routing. These tendencies are probabilistic and controlled through `CONFIG["actor_selection"]`.

Employees are assigned internally to one or more projects. Seniors and managers can span more projects than junior employees. Project membership strongly influences action routing, but non-project employees can still be selected with lower probability.

### Projects

Projects are synthetic business initiatives. Each project has:

- a generated name
- a business domain
- a priority level

Project priority affects task selection pressure. Higher-priority projects are more likely to receive work and more likely to involve senior coordination roles.

### Bottleneck Employees

Bottleneck employees are sampled from the employee population after public employee attributes and hidden capacities are generated.

Selection is weighted by `CONFIG["bottlenecks"]["seniority_selection_weights"]`. Senior and manager employees receive additional selection pressure because they often occupy high-leverage roles such as reviewer, approver, architect, deployer, or meeting organizer.

Each bottleneck receives one hidden reason from `CONFIG["bottlenecks"]["reason_weights"]`:

- `overloaded`
- `underperforming`
- `overloaded_underperforming`

The reason determines which hidden multipliers are changed:

- overloaded employees receive higher response delays and higher routing/meeting/message multipliers
- underperforming employees receive lower speed and somewhat higher response delays
- overloaded-underperforming employees receive both effects

These labels are never written to public CSV files.

### How Bottlenecks Manifest

Bottleneck employees differ from regular employees through observable downstream effects:

- Tasks involving them tend to have longer gaps between assignment, task event, review, approval, QA, and deployment timestamps.
- Work assigned to them tends to remain open longer in `TASK_ASSIGNMENT`.
- They can appear disproportionately often in coordination-heavy tables such as `CODE_REVIEW`, `APPROVAL`, `DEPLOYMENT`, `MEETING`, and `MESSAGE_METADATA`.
- Pipelines that require their approval, review, or deployment authority can complete later than similar pipelines that do not involve them.
- Overloaded bottlenecks often have high meeting attendance, high meeting organization counts, and high message volume.
- Underperforming bottlenecks are more visible through long assignment durations and slow task progress.

The signal is intentionally indirect. A high number of actions alone is not sufficient: some high-volume employees are legitimately senior or managerial. A useful analysis should combine load, role, event timing, assignment duration, pipeline duration, and task complexity/risk.

### Actor Selection

Each pipeline step requests an actor type, such as:

- creator
- assigner
- implementer
- reviewer
- security reviewer
- architect
- QA tester
- approver
- deployer
- triager
- meeting organizer
- meeting participant

`CONFIG["actor_selection"]` defines the probabilistic routing model for each actor type. It combines:

- seniority weights
- department weights
- project membership multipliers
- hidden skill/capacity/authority weights
- bottleneck routing and meeting multipliers where applicable

This makes responsibilities realistic but not deterministic. For example, seniors are much more likely to review code, but a mid-level employee can still review. Managers are much more likely to approve work, but a senior can also approve.

### Work Scheduling

Each employee has an internal `available_at` timestamp. When an action is assigned:

1. The action cannot start before the task is ready.
2. The action cannot start before the employee is available.
3. Non-emergency work is moved into working hours.
4. A response delay is sampled from `CONFIG["action_model"]["response_delay_hours"]`.
5. The delay is adjusted by priority and the employee's hidden `response_multiplier`.
6. A work duration is sampled from `CONFIG["action_model"]["base_duration_hours"]`.
7. Duration is adjusted by complexity, risk, priority, and the employee's hidden `speed_multiplier`.
8. The employee's `available_at` is advanced to the action completion time.

This mechanism is the main way bottlenecks create delays. Overloaded employees respond later; underperforming employees take longer to complete work; overloaded-underperforming employees do both.

Emergency work can occur outside normal working hours. Standard work is constrained by the configured workday.

### Pipelines

Tasks are generated through pipeline templates. A regular task usually corresponds to one pipeline instance. The pipeline can be reconstructed by grouping `TASK_EVENT` rows by `task_id` and sorting by `timestamp`.

Pipeline families include:

- standard delivery
- bug fix
- feature idea
- large feature
- customer complaint
- security vulnerability
- maintenance

Pipeline selection is probabilistic and controlled by `CONFIG["pipelines"]["pipeline_mix"]`. Weekends can alter the mix through `CONFIG["pipelines"]["weekend_multiplier_by_pipeline"]`.

Each pipeline samples:

- project
- priority
- complexity
- risk
- creation timestamp
- optional review changes
- optional QA/testing branches
- optional incidents
- deployment type

#### Standard Delivery

Standard delivery pipelines represent routine product or engineering work.

Typical sequence:

```text
task_created
task_assigned
implementation
code_review
optional requested_changes
optional rework_implementation
optional re_review
optional qa_testing
optional qa_bug_fix
optional qa_retest
deployment_approval
deployment
```

This pipeline produces records in `TASK`, `TASK_EVENT`, `TASK_ASSIGNMENT`, `CODE_REVIEW`, optionally `QA_TEST`, optionally `APPROVAL`, and `DEPLOYMENT`.

#### Bug Fix

Bug fix pipelines begin with a reported bug and include triage, assignment, implementation, review, deployment, and incident verification.

Typical sequence:

```text
bug_reported
triage
task_assigned
fix_implementation
code_review
optional requested_changes
optional fix_rework
optional re_review
deployment
incident_verification
```

Bug fixes can create `INCIDENT` rows and often involve support, engineering, QA, and deployment roles.

#### Customer Complaint

Customer complaint pipelines model support-driven escalations.

Typical sequence:

```text
customer_complaint
support_escalation
engineering_investigation
hotfix_implementation
senior_approval
emergency_deployment
```

These pipelines are likely to create incidents and emergency deployments. They are useful for detecting bottlenecks in escalation, approval, and deployment paths.

#### Security Vulnerability

Security vulnerability pipelines model urgent security work.

Typical sequence:

```text
security_vulnerability_detected
severity_assessment
patch_implementation
security_review
deployment_approval
emergency_deployment
```

These pipelines tend to involve security reviewers, senior engineers, approvers, and deployers.

#### Feature Idea

Feature idea pipelines model product-driven work from approval through rollout.

Typical sequence:

```text
feature_idea
product_approval
technical_design
architecture_review
implementation
qa_testing
optional qa_bug_fix
optional qa_retest
canary_deployment
full_rollout
```

These pipelines create strong signals around product approval, architecture review, QA, and staged deployment.

#### Large Feature

Large feature pipelines are represented by a parent task and multiple child subtasks.

The parent task begins with product approval, design, architecture review, and subtask decomposition. Child subtasks then run parallel implementation and review/testing branches. The parent task is blocked by child subtasks through `TASK_DEPENDENCY` rows.

Typical parent sequence:

```text
feature_idea
product_approval
technical_design
architecture_review
subtask_decomposition
integration_testing
release_approval
deployment
```

Typical subtask sequence:

```text
task_assigned
parallel_implementation_N
code_review
optional rework_implementation
optional re_review
qa_testing
```

For large features, reconstructing the full pipeline requires using `TASK_DEPENDENCY`:

- `blocked_task_id` is the parent large-feature task
- `blocking_task_id` is a child subtask

### Collaboration Activity

#### Meetings and Messages

Meetings and background messages are generated independently of task pipelines, but they use the same employee profiles.

Meetings are sampled daily. Organizer and participant selection is weighted by seniority, department, project membership, and hidden bottleneck meeting multipliers. Meeting attendance advances employee availability, so high meeting load can also delay task work.

Messages are sampled daily and as handoff messages between employees in task pipelines. Sender and receiver selection is affected by seniority and hidden message multipliers. Message volume is a public signal of coordination load, but it is intentionally noisy.

### Delivery Records

#### Reviews, QA, Approvals, and Deployments

Code review outcomes depend on pipeline type, complexity, and risk. Some reviews request changes, which inserts rework and re-review steps.

QA tests can pass or fail. Failures produce bug counts and can trigger fix/retest work.

Approvals are performed by employees selected through approval routing. Higher risk work can lead to conditional approvals.

Deployment records include deployment type, approver, deployment time, and whether rollback was required. Rollback probability depends on risk and deployment type.

#### Incidents

Incidents are generated for bug, customer complaint, and security-oriented work. Each incident is linked to a task and an owner. The incident resolution time follows the task pipeline completion path.

Incident rows help identify employees involved in escalation and remediation paths.

#### Reconstructing Pipelines

For most tasks, `task_id` is the pipeline instance. It is possible to reconstruct a pipeline in the following way:

1. Select one `task_id`.
2. Sort its `TASK_EVENT` rows by `timestamp`.
3. Join supporting rows from `TASK_ASSIGNMENT`, `CODE_REVIEW`, `QA_TEST`, `APPROVAL`, `DEPLOYMENT`, and `INCIDENT`.
4. Compare event gaps and assignment intervals to identify where time was spent.

Large features require one additional step: use `TASK_DEPENDENCY` to attach child subtasks to the parent task.

There is no explicit `pipeline_id` column. The pipeline family can be inferred from `TASK.task_type` and event names.
