# HCMUTE ARS - Privacy notice (deployment template)

This is a product notice template, not legal advice. The operating institution
must review it against applicable law, its actual hosting region, contracts,
and configured service providers before collecting real student data.

## Data handled

The service can store teacher account details, class rosters (roll number,
student name, student ID, and teacher-entered notes), attendance/presence,
question responses, exam attempts, scores, and session/security data.

## Purpose and access

Data supports classroom response, presentations, app-based exams, marking,
analysis, exports, account security, and service operation. Teacher access is
restricted to rooms owned by that teacher account. Exam access codes and
attempt tokens must be treated as credentials.

## Retention and deletion

The current product does not automatically expire class or exam records.
Teachers or authorized operators must delete data when it is no longer needed.
Backups may retain deleted records until the corresponding backup is securely
removed under the operator's backup policy.

## Service providers and location

Deployments may configure SMTP/SMS for password recovery and an MQTT broker
for classroom devices. Hosting location, subprocessors, and cross-border
processing depend on the operator's deployment and must be disclosed by that
operator. The application does not bundle a third-party frontend CDN.

## Security and requests

Operators are responsible for HTTPS, secret management, access control,
backup protection, incident response, and handling requests to correct or
delete data. Students should contact their teacher or institution's designated
privacy contact. The operator must publish a real contact address before
launch.

## Launch checklist for the operator

- Add the institution's legal name and privacy contact to this notice.
- Document actual hosting region, SMTP/SMS/MQTT providers, and subprocessors.
- Obtain the institution's legal review and approve a data-retention schedule.
- Establish a process for access, correction, deletion, and incident requests.
- Restrict and encrypt database backups; test restoration and securely expire
  backup copies according to the institution's policy.
