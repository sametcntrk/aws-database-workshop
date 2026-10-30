# AWS Database Workshop

A hands-on workshop in which ten AWS Engines each power one part of the Lale Market Storefront, so participants can see which data type fits which job.

## Language

### Engines and apps

**Engine**:
A managed AWS data service that represents one data-type category of the workshop (for example DynamoDB for key-value, Neptune for graph). The workshop has ten Engines.
_Avoid_: database (when the specific AWS service is meant), backend

**Engine App**:
The single application instance bound to exactly one Engine. It owns one Storefront Section and serves the Report Screen of its Engine, if one exists. An Engine App never talks to a second Engine.
_Avoid_: service, microservice, backend

**Domain**:
The shared e-commerce scenario (customers, orders, products, carts, sessions, activity, metrics, relationships, images, search) from which every Engine App takes its data. Each Engine models the slice of the Domain that suits its data type.

### Storefront

**Lale Market**:
The fictional high-scale e-commerce company of the workshop and its course. The Storefront carries its brand.

**Storefront**:
The Lale Market web shop that participants use. It is one site to the participant, but each Storefront Section belongs to a different Engine App.
_Avoid_: dashboard, demo site

**Storefront Section**:
The part of the Storefront that one Engine App owns, for example the cart (DynamoDB) or the search page (OpenSearch).
_Avoid_: page, module

**Report Screen**:
A reporting or monitoring view that one Engine App serves for its Engine (for example sales reports on Redshift or live operations charts on InfluxDB). Every Visitor can open it; it changes no data.

**Shared Catalog**:
The Domain data that all Visitors see: products, customers, stores and past orders.

**Visitor**:
A participant's browser identity on the Storefront. A Visitor's cart, orders and browsing history belong to that Visitor only.
_Avoid_: user, customer (a Customer is a record in the Shared Catalog)

**Persona**:
A Customer from the Shared Catalog that a Visitor chooses to shop as, so that history and recommendations exist from the first page.

### Teaching

**Behind-the-Scenes Panel**:
The panel next to the Storefront that shows, for each Visitor action, what the Engine App did: the query or API call, its parameters, the response, the duration and the Engine metrics.
_Avoid_: debug panel, console

**Tutorial**:
Removed on 2026-10-31 together with the Free e-commerce app. The step-by-step guide is now the Guided mission (see Guided journey); an E2E tutorial is a separate page per Engine.

**Experiment**:
A choice on a Storefront Section that changes how the Engine App uses its Engine (for example strongly vs eventually consistent reads), so the Visitor can compare the results in the Behind-the-Scenes Panel.
_Avoid_: toggle, option

**Load Simulation**:
A bounded burst of synthetic shopper requests that an Engine App sends to its Engine to show throughput and latency at scale. It has a fixed upper limit.

### Operations

**Admin Console**:
The instructor-only page that Seeds and resets the Shared Catalog, clears Visitor data and turns Load Simulation on or off.

**Seed**:
The act of an Engine App generating synthetic Domain data and writing it to its Engine. Only the Admin Console starts a Seed.

**Instructor Stack**:
The environment the instructor creates in one step from the CloudFormation template.

**Participant Build**:
The same environment, with the same configuration values, that a participant creates manually by following the step-by-step guide.
