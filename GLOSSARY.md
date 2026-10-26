# Glossary

**Engine**
A managed AWS data service that represents one data-type category of the workshop (for example DynamoDB for key-value, Neptune for graph). The workshop has ten Engines.

**Engine App**
The single application instance bound to exactly one Engine. It writes its own data to that Engine, reads the same data back, and shows it on a web page. An Engine App never talks to a second Engine.

**Seed**
The act of an Engine App generating synthetic Domain data and writing it to its Engine.

**Read**
The act of an Engine App querying back the data it seeded, in the access pattern that is natural for that Engine.

**Domain**
The shared e-commerce scenario (customers, orders, products, carts, sessions, activity, metrics, relationships, images, search) from which every Engine App seeds data. Each Engine models the slice of the Domain that suits its data type.

**Dashboard**
The landing page that lists all Engine Apps and links to each one.

**Instructor Stack**
The environment the instructor creates in one step from the CloudFormation template.

**Participant Build**
The same environment, with the same configuration values, that a participant creates manually by following the step-by-step guide.
