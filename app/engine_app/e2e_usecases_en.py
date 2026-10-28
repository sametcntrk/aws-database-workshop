"""English text of the DynamoDB use cases (e2e_usecases.py), in ASD-STE100 style.

The Turkish text in e2e_usecases.py is the source that the owner reviewed. This file gives the English text of each field.
Structure per use case: title, key, story, reqs = [(want, why) x 5], scores = {cand: [reason x 5]}, h2h = {cand: text}, verdict.
e2e_usecases.apply_en() merges it into the (en, tr) tuples."""

EN = {
    "cart": {
        "title": "Shopping carts (Lale Market)",
        "key": "Key: cart, then product. Value: quantity, price, expiry.",
        "story": "The product page of Lale Market has an \"Add to cart\" button. The button adds a row to the cart with the visitor id from the browser cookie. If the row exists, the button increases its quantity. "
                 "The cart page shows all rows with price and quantity. The checkout reads the final cart, writes the order to Aurora together with the stock and the customer records, and then empties the cart. "
                 "The rule of the store: at most 5 units of one product in one cart. On a normal day there are 250 cart writes per second. On a campaign evening, at 20:00, the traffic goes to 5,000 writes per second in ten minutes and stays there for three hours. "
                 "70 percent of the visitors leave their cart. One day later those carts have no value. The team has three developers and no database administrator.",
        "reqs": [
            ("Each request knows the visitor id. There are two questions. One: \"all rows of this cart, in product order\". Two: \"add 2 units of this product to this cart, but the total must not go above 5\". "
             "The second question is a rule. The rule must hold also when two browser tabs add at the same time. Carts are independent: no question reads two carts at once.",
             "The cart page asks for all rows each time it opens. A read row by row makes the page slow. If the limit of 5 does not hold, one customer can buy 50 units of a campaign product and the stock plan fails. "
             "If the application protects the rule with \"read first, then write\", two tabs race and the limit is exceeded."),
            ("On a normal day 250 writes and 1,000 reads per second. On a campaign evening 5,000 writes and 20,000 reads per second in ten minutes. This lasts three hours and then goes down. "
             "At the peak each request must return in less than 20 ms. Before the campaign, nobody must resize the database by hand.",
             "These are the three hours with the most sales of the year. If the cart is slower than 20 ms, the visitor clicks the button a second time or gives up. If a manual resize is forgotten or late, the system fails in the middle of the campaign."),
            ("A lost cart is acceptable but not wanted: the customer adds the products again and is angry. There is no money loss, because the order is durable in Aurora. "
             "Still, an Availability Zone failure must not lose all carts.",
             "The cart is a preparation, not the record. So durability is a preference here. But the loss of 50,000 carts in an AZ failure on a campaign night is a large loss of sales."),
            ("Three developers, no database administrator. The team does not want to size instances, apply patches, or make a capacity plan before the campaign. The team knows the AWS SDK.",
             "In a small team, operations time is time taken from product work. A capacity plan before each campaign is a risk meeting each time."),
            ("The traffic changes a lot: 27 days of the month low, 3 evenings very high. The team wants to pay almost nothing in quiet time and pay for usage in busy time. The cart data is small (less than 1 KB per cart).",
             "A server sized for the peak and running all month is idle for 95 percent of the month, and you pay for it. With small data, the price per GB is not important and the price per request decides."),
        ],
        "scores": {
            "ddb": ["Partition key = cart, sort key = product (F3): the full cart is one Query. The rule \"at most 5\" holds in one write with a condition on the UpdateItem (F5). If two tabs race, the second one is rejected. "
                    "2 points off: the checkout has two steps (read the cart, write the order to Aurora, delete the cart). These two steps are not one transaction. After a failure an old cart can stay, and the application must clean it.",
                    "Writes spread over partitions by the visitor id (F2). On-demand mode follows the traffic: the step from 250 to 5,000 writes per second needs no setting. Reads and writes by key take single-digit milliseconds also at the peak. No points off.",
                    "Each write is stored in several Availability Zones before DynamoDB accepts it. An AZ failure loses no cart. 2 points off: an eventually consistent read of the cart can miss an addition from one second before. The checkout needs a strongly consistent read, and that costs two times the read units.",
                    "Serverless: no instance, no patch, no capacity plan. The team works with the AWS SDK that it already uses. No points off.",
                    "In on-demand mode you pay per request and per GB stored. On quiet days the cost is almost zero. 1 point off: on a campaign evening, strongly consistent reads and conditional writes use more units than normal requests. The peak cost must be calculated."],
            "aur": ["The cart, the rows and the stock are in the same database. The limit of 5 holds with a CHECK or with UPDATE ... WHERE qty + 2 <= 5. The checkout protects the cart, the stock and the order in one transaction. All questions are SQL. No points off. On this requirement Aurora is the strongest candidate.",
                    "5,000 small writes per second are within reach of one large writer instance, and Aurora Serverless v2 increases the capacity (ACU) in seconds. 2 points off: all writes go through one writer, so there is a known upper limit. For a ten-minute jump you must keep the minimum ACU high or test the scaling before the campaign.",
                    "Six copies in three AZs, continuous backup. No points off.",
                    "Managed service: backup, patches and failover are done by AWS. 3 points off: the schema, the indexes and the ACU range are decisions of the team. For a team of three with no database administrator, the capacity and the connection pool settings before a campaign are extra work.",
                    "Serverless v2 is paid per ACU-hour. 3 points off: on the 27 quiet days you also pay the minimum ACU. For a small and variable workload like the cart, this is more expensive than pay per request. If an Aurora cluster already exists for the orders, this extra cost is small."],
            "ec": ["The cart is a hash: HGETALL reads the full cart, HINCRBY increases the quantity of one product atomically (the in-memory form of F5). 4 points off: HINCRBY has no condition \"not above 5\". You need a Lua script or a two-step WATCH/MULTI operation, and the application code carries the rule.",
                   "Answers in microseconds from memory, and Serverless scales by itself. No points off.",
                   "ElastiCache Serverless keeps replicas in several AZs, but it has no durable log that writes each write to disk. A failure can lose the carts of the last seconds. 6 points off: the loss of carts in an AZ failure is not wanted but accepted in this workload.",
                   "Serverless, no instance. 1 point off: the Lua script becomes a maintenance task of the team.",
                   "You pay for the data stored and for the requests (ECPU). 3 points off: the data is in memory, so the price per GB is much higher than on disk. The cart data is small, but a minimum fee is paid also on quiet days."],
        },
        "h2h": {
            "aur": "Head to head with relational (Aurora). The requirements where they differ: the rule part of R1, R2 and R5. The strength of Aurora shows at the checkout: the cart, the stock and the order are written in one transaction. In DynamoDB this is two steps, and an old cart can stay after a failure. "
                   "The strength of DynamoDB shows on the campaign evening. Nobody does anything for the step from 250 to 5,000 writes. On quiet days the payment is almost zero. In Aurora the writer has an upper limit and a minimum ACU. "
                   "In this workload the key-value store is selected, because the cart is a preparation and not the record. The order is already durable in Aurora, and the two-step checkout of the cart is an acceptable price. "
                   "Which condition would make Aurora the selection: if the cart and the stock had to be locked at the same time. Example: a product added to the cart is taken from the stock. Or: if the campaign traffic stayed within the easy reach of one writer and the traffic was flat. If the store already operates an Aurora cluster and the extra cost is small, Aurora is also a decision that you can defend.",
            "ec": "Head to head with in-memory key-value (ElastiCache). The requirements where they differ: R3 durability and the rule part of R1. The strength of ElastiCache is speed: microseconds and an exact expiry. "
                  "But for a cart, this speed is more than enough. The limit of 20 ms is easily met by the single-digit milliseconds of DynamoDB. The difference is durability: ElastiCache Serverless has no durable write log, so a failure can lose the last carts of the campaign night. "
                  "The limit of 5 also needs a Lua script in ElastiCache. In DynamoDB it is one condition. So between the two key-value stores, the durable one is selected: the same category, the same speed class, but no risk of loss. "
                  "Which condition would make ElastiCache the selection: if the cart read was in front of each page request and less than one millisecond was necessary. Or: if the cart was already durable in another system and the copy here was only a cache.",
        },
        "verdict": "Decision: DynamoDB 45, Aurora 42, ElastiCache 36. All three candidates can carry the workload. The difference is in the weight of the requirements. The cart is not the record and the traffic is variable. So R2 and R5 weigh more than the rule part of R1, and this puts DynamoDB in front. "
                   "If we still select key-value, our gains: on the campaign night nobody touches the database. The cart rule holds in one request. Left carts go away by themselves. Almost zero cost on quiet days. "
                   "Our possible losses: the checkout has two steps and an old cart can stay after a failure. The application must clean it and must use a strongly consistent read at the checkout. If one condition changed: if the cart and the stock had to be locked in one transaction, Aurora would win.",
    },

    "profile": {
        "title": "User profiles and preferences",
        "key": "Key: user id. Value: name, language, addresses, notification preferences.",
        "story": "A music application has five million users. At each screen start, the application reads the name, the language, the subscription status and the notification preferences of the user. This read happens on each request. "
                 "A profile changes about once a month: an address is added, a preference is turned off. Each quarter the marketing team adds a new field to the profile (\"wants podcast suggestions\", \"birthday\"). This field starts with a value only for new users. "
                 "30,000 profile reads per second, 100 writes. Peaks at 9:00 and 21:00, low at night. Each read must take less than 10 ms, because the screen is drawn from the profile. The team has five developers, knows the AWS SDK, and does not want servers.",
        "reqs": [
            ("One question: \"the profile of this user id\". The application knows the id from the login. The profile is one object: it contains nested fields such as an address list and a preference map. A change of one preference must not rewrite the full profile. "
             "Profiles are independent: no question reads two profiles at once.",
             "Each screen starts with this read. If it is slow, each screen is slow. A rewrite of the full profile for one preference can overwrite a change made at the same time from another device."),
            ("30,000 reads and 100 writes per second, with peaks in the morning and in the evening. Each read in less than 10 ms. The number of users doubles each year. The team does not want a redesign for growth.",
             "The read volume is 300 times the write volume, so the scale is on the read side. Growth of two times a year, in a system with sized instances, means one resize project each year."),
            ("The profile is durable data. If it is lost, the user enters the address and the preferences again. There is a loss of trust, no loss of money. An AZ failure must not lose profiles.",
             "The loss of a user profile is a support ticket and a loss of trust. In a large application, an AZ failure touches hundreds of thousands of users."),
            ("A new field each quarter, with no migration and no downtime. The team does not want servers, patches or index maintenance. The team knows the AWS SDK, and knows the MongoDB API and SQL only a little.",
             "A schema change or a migration window each quarter ties the calendar of the marketing team to the database team. A team that learns a new API makes errors."),
            ("Read-heavy and regular. Pay per request or per capacity, both are possible. The profile is small (less than 4 KB). The total cost must grow in a straight line with growth, not in jumps.",
             "30,000 reads continue for most of the day. In flat traffic, capacity bought in advance can be cheaper than pay per request. In growth, a jump to the next instance class doubles the cost in one night."),
        ],
        "scores": {
            "ddb": ["Simple primary key = user id. GetItem is one read (F1). One preference is changed with UpdateItem through a document path (SET prefs.podcast = :v), and the full profile is not rewritten. 1 point off: a change inside a list, such as \"change the second address\", uses the index number of the list. The application must know this number.",
                    "Reads spread over partitions (F2). 30,000 reads are served with on-demand mode or auto scaling, in single-digit milliseconds. For growth of two times a year, nothing changes. No points off.",
                    "Each write is stored in several AZs. Point-in-time recovery can be turned on. No points off.",
                    "A new field is written only to new values (F4). There is no migration. Serverless, and the team uses the SDK that it knows. 1 point off: the value limit of 400 KB makes the design difficult if the profile grows. Example: the listening history is added to the profile. The history must go to a separate table.",
                    "In flat traffic, provisioned mode with auto scaling is the cheapest option. In a variable start, on-demand. The cost grows in a straight line with the number of users. 1 point off: profiles larger than 4 KB use two read units. The profile size must be monitored."],
            "doc": ["The profile is a natural document: find by _id is one read. With updateOne, a nested field or one address in the list ($set, arrayFilters) is changed without a rewrite of the full profile. A change inside a list is more natural than in DynamoDB. No points off.",
                    "Reads spread over up to 15 replicas, and 30,000 reads are served. 2 points off: the team selects the number of replicas and the instance class. Growth of two times a year is a resize step, and all writes go through one primary.",
                    "Six copies in three AZs, continuous backup. No points off.",
                    "The schema is free, a new field needs no migration. Backups and patches are managed. 3 points off: instance sizing and replica management are tasks of the team, and the MongoDB API is new for this team.",
                    "Instances are paid per hour and per I/O. 3 points off: the instances also run at night with low traffic. When growth needs the next instance class, the cost jumps."],
            "aur": ["A read by primary key is one index lookup. If the profile is in a JSONB column, a nested field is changed with jsonb_set. 1 point off: a JSONB update rewrites the full row (MVCC). For one field you pay the cost of the full row.",
                    "Reader instances carry 30,000 reads. 3 points off: the team selects the number and the class of the readers. Growth is a capacity project.",
                    "Six copies in three AZs. No points off.",
                    "Managed service. 3 points off: a field outside the JSONB needs a schema change. The team knows SQL only a little. The connection pool and the reader routing are set in the application.",
                    "ACU-hours or instance-hours. 3 points off: in low traffic you also pay the minimum capacity."],
        },
        "h2h": {
            "doc": "Head to head with document (DocumentDB). This is the comparison where a reader most often says \"why not that one?\". A profile is a full document, and both stores have no schema. The requirements where they differ: R2 and R4. "
                   "The strength of DocumentDB shows in R1. It supports directly the update of nested fields, of lists and of one element in a list ($set, $push, arrayFilters). It also supports queries on the content of the profile (\"users with language Turkish\"). In DynamoDB, a change inside a list needs the index number, and a query on the content of the value needs a GSI (F7). "
                   "The strength of DynamoDB shows in R2 and R4: for 30,000 reads and growth of two times a year, no sizing is done. The writes do not all go through one primary instance, and the team works with the SDK that it knows. In DocumentDB, the number of replicas, the instance class and the MongoDB API are new tasks of the team. "
                   "In this workload the key-value store is selected, because the only access pattern is \"profile by id\". There is no query on the content of the profile, and the scale must grow on the read side by itself. The flexible query power of the document database is a power that would not be used here, and its price is operations. "
                   "Which condition would make DocumentDB the selection: if questions on the content of the profile were frequent and varied (\"users in Istanbul who want podcasts\"). Or: if the profile had long lists that change often. Or: if the team already knew MongoDB and operated a DocumentDB cluster.",
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R2, R4 and R5. The strength of Aurora shows if the profile is queried together with other relational data (subscription invoices, payment methods). With a JOIN, \"users whose subscription ends and who want notifications\" is one query. "
                   "In DynamoDB this question is two reads, or a task for the analytics copy. But in this workload the profile is read and written alone. No JOIN is used. The scale is on the read side. The sizing of reader instances and the schema change for a new field are tasks that the team does not want. "
                   "So the key-value store is selected. Which condition would make Aurora the selection: if the profile was updated in the same transaction as the subscription and the payment data. Or: if reports were often asked by profile fields. Or: if the application was already built on Aurora and the profile was only one more table.",
        },
        "verdict": "Decision: DynamoDB 47, DocumentDB 42, Aurora 40. All three candidates fully meet R1 and R3. R2 and R4 decide the race: read scale with no sizing, and the SDK that the team knows. "
                   "If we still select key-value, our gains: no project for growth. No migration for a new field. 30,000 reads served by themselves. Cost in a straight line with the number of users. "
                   "Our possible losses: a question on the content of the profile (\"users with language Turkish\") needs a GSI, or it goes to the analytics copy. Changes inside lists need index numbers. If the profile comes near 400 KB, growing fields such as the history go to a separate table. If one condition changed: if questions on the content of the profile were frequent and varied, DocumentDB would win.",
    },

    "session": {
        "title": "Sessions and login tokens",
        "key": "Key: session id. Value: user id, role, last page, expiry.",
        "story": "Each HTTP request of a web store reads the session with the session id from the cookie. The session says who the user is, which role, and if there is a cart. A session ends after 30 minutes without activity, and each page view renews its time. "
                 "40,000 page requests per second, so 40,000 session reads and 40,000 time renewals per second. The session read is in front of each request: 1 ms of latency adds 1 ms to each page. "
                 "A lost session only means a new login. The cart is in DynamoDB and the order is in Aurora, both already durable. The team does not want servers.",
        "reqs": [
            ("One question: \"the session of this session id\". On each request, one read and one time renewal (a write). The session is a small object (less than 1 KB). An expired session must not be read: 30 minutes and 1 second later, the request must go to a new login.",
             "The session read is the first step of each request. The acceptance of an expired session is a security hole: on a shared computer the next person stays in the previous account."),
            ("40,000 reads and 40,000 writes per second, variable during the day. Each read must take less than 1 ms, because it is added to each page request. Even 5 ms is felt on millions of pages a day.",
             "This latency is a tax on each page for each user. The difference between 1 ms and 5 ms is 5 percent of the total time of a product page."),
            ("Low: a lost session is a new login. A new login for all users after an AZ failure is accepted but not wanted.",
             "A session is derived data. Its source is the user account. Its loss is annoying, not harmful. So durability can be given up for speed here."),
            ("The team does not want servers, nodes or patches. Serverless is preferred. The time renewal must be one line in the application code.",
             "The session infrastructure is not the product. It must not take the time of the team. If the renewal is complex, developers skip it and sessions end too early."),
            ("Traffic varies during the day. Pay per request or per usage. The session data is small and short-lived. The total data never goes above a few GB.",
             "For small, short-lived data the GB price is not important and the request price decides. 80,000 requests per second show on the monthly bill."),
        ],
        "scores": {
            "ddb": ["GetItem and UpdateItem by session id are one request each (F1). The TTL field deletes the expired session (F6). 2 points off: the TTL deletion is not exact. It usually happens within a few days. The application must compare expires_at with the current time on each read, or an expired session is accepted.",
                    "40,000 + 40,000 requests are served by on-demand mode (F2). 4 points off: the latency is single-digit milliseconds, not less than 1 ms. The strict limit of this requirement is not met. With DAX, reads go to microseconds, but the write (the renewal) stays in milliseconds, and DAX is one more component.",
                    "Each write is stored in several AZs. A session survives a failure. No points off. The requirement is low, but it is fully met.",
                    "Serverless. The renewal is one UpdateItem. No points off.",
                    "Pay per request. 2 points off: 40,000 writes (renewals) per second are 40,000 write units, and a write costs five times a read. A renewal only after half of the remaining time lowers the cost, but this is a rule in the application."],
            "ec": ["GET and SET, or one hash per session. EXPIRE renews the time on each request, and the key is gone exactly at the end: an expired session is never read. No points off.",
                   "Microseconds from memory, far below 1 ms. Serverless scales by itself. No points off.",
                   "Serverless keeps replicas in several AZs, but it has no durable write log. A failure can lose the last sessions, and users log in again. 5 points off: loss is possible. In this workload it is accepted.",
                   "Serverless. EXPIRE is one command. No points off.",
                   "Pay for data (GB-hours) and requests (ECPU). 2 points off: memory is more expensive per GB than disk, and there is a minimum fee. The session data is small, so the difference is small."],
            "ks": ["SELECT and UPDATE by partition key are one request each. The row TTL ends the session. 1 point off: each renewal rewrites the row with a new TTL, and an expired row stays as a tombstone until it is deleted.",
                   "On-demand capacity follows the load, single-digit milliseconds. 3 points off: less than 1 ms is not met.",
                   "Three copies in three AZs. No points off.",
                   "Serverless. 4 points off: the team learns CQL, a Cassandra driver and the connection settings. A new API for a simple task such as sessions is out of proportion.",
                   "Pay per read and write request. 1 point off: the renewal writes are 40,000 write units per second."],
        },
        "h2h": {
            "ec": "Head to head with in-memory key-value (ElastiCache). This is a race between two members of the same category. The F6 row of the A10 matrix and the speed class decide it. The requirements where they differ: R2 and R3. "
                  "The strength of ElastiCache: reads in microseconds, because the data is in memory, and an exact expiry (EXPIRE), so an expired session is never read. DynamoDB is single-digit milliseconds, and the TTL deletion can take days, so the expiry check stays with the application. "
                  "The strength of DynamoDB: durability. Each write is stored in several AZs, and a failure sends nobody back to the login screen. In this workload the limit \"less than 1 ms\" in R2 is strict and R3 is low. These two conditions together put ElastiCache in front. "
                  "Which condition would make DynamoDB the selection: if the session contained something whose loss is not accepted (for example a half-finished payment step). Or: if the latency limit was 10 ms instead of 1 ms. Or: if sessions were read from several Regions and needed a global table. "
                  "Best practice: derived, small, short-lived and latency-sensitive data such as a session goes to the in-memory store. The durable parts inside the session (cart, order) go to the durable store.",
            "ks": "Head to head with wide-column (Keyspaces). The requirements where they differ: R2, R4 and the expiry part of R1. Keyspaces is also serverless, reads by key, and has a row TTL. In durability it is equal to DynamoDB. "
                  "The difference is in operations and in the API: the team learns CQL and a Cassandra driver and sets a connection pool. In DynamoDB the team writes two calls with the SDK that it knows. Also, each renewal in Keyspaces rewrites the row, and an expired row leaves a tombstone. "
                  "In this workload there is no reason to select Keyspaces, because its strength, Cassandra compatibility, is not used here. Which condition would make Keyspaces the selection: if the team already used Cassandra and CQL. Or: if the sessions moved from an on-premises Cassandra to AWS and the code had to stay unchanged.",
        },
        "verdict": "Decision: ElastiCache 43, DynamoDB 42, Keyspaces 41. This is the closest race, and the category (key-value) is clearly the right one. The question is which store inside the category. The limit \"less than 1 ms\" of R2 and the low R3 put ElastiCache one point in front. "
                   "If we still select DynamoDB, our gains: a session survives a failure. No capacity or memory to think about. The team uses the same SDK as for the other tables. A global table makes multi-Region sessions possible. "
                   "Our possible losses: a few milliseconds are added to each page. The application must check the expiry on each read. 40,000 renewals per second are paid as write units. If one condition changed: if loss was not accepted or the limit was 10 ms, DynamoDB would win.",
    },

    "game": {
        "title": "Game state and player inventory",
        "key": "Key: player, then object type and object id. Value: the fields of the object.",
        "story": "A small studio releases a mobile game. The marketing campaign brings one million players on the first day. One month later the daily players go down to 100,000. Each player has an inventory of 20 to 500 objects. The fields of an object depend on its type: a sword has damage and durability, a potion has duration and effect. "
                 "The game reads the full inventory at each start and only the weapons on the battle screen. When an object is won, it is added to the inventory. When an object is bought, it must not be lost. The studio has two backend developers and no operations team. On release night nobody wants to resize a cluster.",
        "reqs": [
            ("Four questions. The full inventory of this player. Only the weapons of this player. Add this object to this player. Decrease the durability of this object by 3. The player id is known on each request. Players are independent. The fields of objects differ by type, and new object types come with each update.",
             "The inventory is read at each game start. If it is slow, the game starts slowly. If a new object type needs a migration, each game update becomes a database project."),
            ("200,000 requests per second on the first day, 20,000 per second one month later. Each request in less than 10 ms from everywhere in the world. No manual action on release night.",
             "The release happens once and cannot be repeated. A slow game on that night goes into the app store reviews. One month later, ten times less traffic must cost ten times less."),
            ("High: if a bought object is lost, the player asks for a refund. An AZ failure must not lose data.",
             "The inventory is what the player bought with money. Its loss is a direct loss of revenue and of reputation."),
            ("Two developers, no operations team. No sizing, patches or backups wanted. No migration for a new object type.",
             "In a team of two, operations work stops the development of the game."),
            ("The traffic goes down ten times after the release. The cost must go down too. The inventory data is small (less than 100 KB per player).",
             "A cluster sized for the release runs 90 percent empty one month later, and you pay for it."),
        ],
        "scores": {
            "ddb": ["Partition key = player, sort key = TYPE#id (F3): the full inventory is one Query, only the weapons is a slice with begins_with(sk, 'WEAPON#'). Each object carries its own fields (F4). The durability decrease is one atomic ADD on one object (F5). No points off.",
                    "Writes and reads spread over partitions by player id (F2). On-demand mode serves the release night by itself, and one month later the cost goes down with the traffic. With a global table, less than 10 ms is possible in several Regions. No points off.",
                    "Each write is stored in several AZs, point-in-time recovery. No points off.",
                    "Serverless. No change for a new object type. No points off.",
                    "Pay per request. After the release the cost goes down ten times. 1 point off: a read of a full inventory of 500 objects uses several read units. In games that are opened often, the inventory size decides the cost."],
            "doc": ["An object array inside the player document is natural: $push adds, arrayFilters changes the field of one object, a projection returns only the weapons. 1 point off: a change of one object in an array of 500 rewrites the full document.",
                    "Reads scale with replicas. 4 points off: all writes go to one primary instance. For release night the primary is sized large in advance and made smaller one month later. Both are manual tasks.",
                    "Six copies in three AZs. No points off.",
                    "The schema is free, backups and patches are managed. 3 points off: instance sizing is a task of the team, and for a team of two it is a risk on release night.",
                    "Instances per hour. 4 points off: if the instances enlarged for the release are not made smaller by hand one month later, you pay for nothing."],
            "ec": ["One hash per player: HGETALL is the inventory, HSET is one object. 4 points off: the slice \"only the weapons\" does not exist in a hash. The application filters, or keeps one hash per type. An atomic decrease of an object field is possible with HINCRBY, but the rule (not below 0) needs a script.",
                   "Microseconds from memory. Serverless scales. No points off.",
                   "No durable write log. A failure can lose bought objects. 6 points off: in this workload a loss means a refund.",
                   "Serverless. 1 point off: script maintenance.",
                   "GB-hours and ECPU. 3 points off: memory is expensive per GB, and the data of release night stays in memory for a month."],
        },
        "h2h": {
            "doc": "Head to head with document (DocumentDB). The requirements where they differ: R2, R4 and R5. The strength of DocumentDB is in R1: the player is a document and the inventory is an array inside it. The update of one object in the array and a projection of only the weapons are natural in the MongoDB API. "
                   "DynamoDB answers the same questions with the sort key design: each object is a separate object, the weapons are a prefix slice. This is equally direct, but the design must be made in advance. The difference shows on release night. In DocumentDB all writes go through one primary. The team of two must enlarge that primary in advance and make it smaller one month later. In DynamoDB nothing is done, and the cost goes down with the traffic. "
                   "In this workload the key-value store is selected, because the access patterns are known in advance. The release curve (one day of peak, then ten times less) makes a store with no sizing necessary. "
                   "Which condition would make DocumentDB the selection: if the traffic was flat and known in advance. Or: if free queries inside the inventory (\"all my weapons with damage above 50\") were frequent. Or: if the team already knew MongoDB.",
            "ec": "Head to head with in-memory key-value (ElastiCache). The requirement where they differ: R3 durability. ElastiCache is in front of DynamoDB in speed and in scale, but the inventory is what the player bought with money. In a store with no durable write log, a failure means refunds. "
                  "So between the two key-value stores, the durable one is selected. Which condition would make ElastiCache the selection: if the inventory was durable in another place. And: if the copy here was only a cache for fast reads. Then both are used together: the durable record in DynamoDB, the hot copy in ElastiCache. Or: if ranking questions such as a leaderboard (sorted set) were the main work.",
        },
        "verdict": "Decision: DynamoDB 49, DocumentDB 38, ElastiCache 36. This is not a close race: the release curve and durability together put DynamoDB far in front. "
                   "If we still select key-value, our gains: release night and one month later are the same table, and nobody touches it. The inventory is durable. No migration for a new object type. A global table for players in several Regions. "
                   "Our possible losses: ranking questions such as \"the 100 strongest players\" are not answered by key. They need a GSI (F7) or an in-memory sorted set. One inventory with thousands of objects stays in one partition. If one condition changed: with flat traffic and frequent free queries inside the inventory, DocumentDB would enter the race.",
    },

    "iot": {
        "title": "The last state of each device (IoT)",
        "key": "Key: device id. Value: last reading, time, battery, status.",
        "story": "An energy company has two million smart meters. Each meter sends its last value, its battery level and its status every 30 seconds. The messages come through AWS IoT Core to a Lambda function. "
                 "When an operator clicks a meter in a dashboard, its last state is shown. The history goes to a separate time series system. Here only the last state is kept, and each message overwrites the previous one. "
                 "An alarm must open for a meter with a temperature above 80 degrees or a battery below 5 percent. 65,000 messages per second, at every hour of the day, flat. The team uses IoT and Lambda and does not want servers.",
        "reqs": [
            ("Questions: \"the last state of this device\" and \"replace the last state of this device with this message\". The device id is known in each message and on each click. Devices are independent. The history is not asked, only the last value.",
             "The dashboard shows one device. There are no questions other than these two. If the model is more complex than this, the complexity is paid for nothing."),
            ("65,000 writes per second, flat and continuous, 5.6 billion messages a day. Few reads: 200 per second. A write must be accepted in less than 50 ms, or the Lambda queue grows and messages are late.",
             "The write volume is the whole of this workload. If writes become slow, the IoT queue fills, messages are dropped, and the dashboard shows an old value."),
            ("Medium: a lost last state comes again 30 seconds later. Even in an AZ failure, a state older than 30 seconds must not be shown.",
             "The data renews itself every 30 seconds. Durability is a comfort here, not an obligation."),
            ("The team uses AWS IoT, Lambda and the SDK. No servers, nodes or CQL. The alarm logic must be separate from the code that writes.",
             "If the alarm rule goes into the Lambda that writes the message, each new rule changes that function and slows the write path."),
            ("The write count is constant and high. The price per write decides. The traffic is flat, so capacity can be bought in advance, and this must be cheaper than on-demand. The data is small (1 KB per device).",
             "5.6 billion writes a day: a difference of 10 percent in the price of a write unit is thousands of dollars a month."),
        ],
        "scores": {
            "ddb": ["Simple primary key = device id. Each message overwrites the last state with PutItem, and the dashboard reads with GetItem (F1). There is no simpler model. No points off.",
                    "Two million different keys spread the writes equally over partitions (F2). 65,000 writes are accepted in single-digit milliseconds. No points off.",
                    "Each write is stored in several AZs. 1 point off: an eventually consistent read can show a value one second old. If the dashboard reads strongly consistent, it costs two times the read units, but reads are few.",
                    "Serverless, the SDK that the team knows. The change stream (F8, Streams in B5) gives each change to a separate Lambda, and the alarm rule is separate from the code that writes. No points off.",
                    "In flat traffic, provisioned capacity with reserved capacity is clearly cheaper than on-demand. 1 point off: 65,000 write units are paid continuously. Messages above 1 KB use two units, so the message size must be kept small with discipline."],
            "ks": ["INSERT by partition key overwrites (in Cassandra, insert = upsert), SELECT by partition key reads. No points off.",
                   "Writes spread over partitions. On-demand or provisioned capacity. 1 point off: it is fast because no LWT is used. But the provisioned capacity for 65,000 writes must be calculated in advance, and the price per request in on-demand is high.",
                   "Three copies in three AZs. No points off.",
                   "Serverless. 5 points off: the team learns CQL, a Cassandra driver and the connection settings. For the alarm there is a CDC stream, but its connection to Lambda needs more setup than the stream of DynamoDB.",
                   "Pay per write request, provisioned mode. 2 points off: the price of a write unit is similar to DynamoDB, but CDC is charged separately and there is no reserved capacity."],
            "ix": ["The device is a tag, the measurements are fields. A \"last value\" query (last()) exists. 4 points off: a time series database stores each message as a point and does not overwrite. The question \"last state\" is a search for the last point of a series. This is not as cheap as a direct read by key.",
                   "Built for a high write rate. 65,000 points per second are within reach of one instance. 1 point off: the instance class is selected in advance.",
                   "A replica with the Multi-AZ option. 1 point off: the replica is selected by hand.",
                   "Managed instance. 4 points off: instance sizing, disk and retention settings are tasks of the team. For the alarm, a separate task or alert engine must be learned.",
                   "Instance per hour and disk. 4 points off: a time series instance only for the last state is an unnecessary cost, because the history of this data is kept elsewhere."],
        },
        "h2h": {
            "ks": "Head to head with wide-column (Keyspaces). The requirements where they differ: R4 and R5. In data model and in scale, Keyspaces is almost the same as DynamoDB: overwrite by key, spread over partitions, three copies. "
                  "The difference is in the team and in the integration: Keyspaces needs CQL and a Cassandra driver. DynamoDB is the SDK that the team already uses with IoT and Lambda. For the alarm, the change stream of DynamoDB (F8) connects directly to Lambda, and Keyspaces CDC needs more setup. "
                  "In this workload key-value (DynamoDB) is selected, because the only advantage of Keyspaces, Cassandra compatibility, is not a need here. Which condition would make Keyspaces the selection: if the current meter system of the company ran on Cassandra. And: if it moved to AWS with no code change. Or: if the team knew Cassandra well and DynamoDB not at all.",
            "ix": "Head to head with time series (Timestream for InfluxDB). The requirements where they differ: R1, R4 and R5. This comparison shows a limit: for the same device data, \"last state\" and \"history\" are two different workloads. "
                  "A time series database stores each message as a point. Its strength is time ranges, windows and sums: \"the average of the last hour\", \"the peak value of yesterday\". The only question here is \"the last value\". For this question, to store each message, to search for the last point, and to operate an instance for it is unnecessary. "
                  "So key-value is used for the last state and time series for the history. The two stores are not alternatives to each other. They complete each other. Which condition would make time series the selection: if the dashboard showed a chart and an average next to the last value. And: if there was no separate history system. Then time series is selected as the one store, and the \"last value\" query is answered inside it.",
        },
        "verdict": "Decision: DynamoDB 48, Keyspaces 42, InfluxDB 36. A clear win. The workload is the exact definition of the key-value model: overwrite by key, independent devices, flat and high writes. DynamoDB loses no points on a must requirement. "
                   "If we still select key-value, our gains: the simplest model. The SDK that the team knows. The change stream separates the alarm from the code that writes. Reserved capacity pays the flat traffic at the lowest price. "
                   "Our possible losses: questions such as \"the average of the last hour\" do not exist in this table. A time series database is also necessary for the history. The bill for 65,000 write units is sensitive to the message size. If one condition changed: if the history and the last state were wanted in one store, a time series database would be the only candidate.",
    },

    "idem": {
        "title": "Idempotency keys for payments and APIs",
        "key": "Key: request id. Value: result, time, expiry.",
        "story": "A payment API charges cards. After a network error, the client sends the request again with the same request id. The system must charge the card once and must return the result of the first request to the second request. "
                 "20 million requests a day, 2 percent of them repeats. The mark must be kept for 24 hours. The payment record itself is in a separate relational database. The payment team requires multi-AZ and does not want servers.",
        "reqs": [
            ("\"Was this request id processed before? If not, mark it now\" must be one atomic step. If two requests with the same id come in the same millisecond, only one must get the answer \"new\". If it was processed, the first result must be returned.",
             "If the check and the mark are two separate steps, two repeats at the same time both see \"new\" and the card is charged twice. This is exactly the error that must be prevented."),
            ("230 requests per second on average, 3,000 at the peak. Each check in less than 10 ms, because it is the first step of the payment flow.",
             "The volume is low. Here the scale is not important. Correctness and latency at the peak are important."),
            ("Very high: if the mark is lost, a repeated request looks \"new\" and the card is charged twice. Even an AZ failure must not lose a mark. On this card, this requirement is a must.",
             "A double charge is a direct loss of money and of customers. Even a \"loss of a few seconds\" in a failure is not acceptable."),
            ("Payment team, no servers, multi-AZ required. The marks must delete themselves after 24 hours.",
             "The payment team has compliance obligations. One more component to operate is one more component in the audit scope."),
            ("Low volume. Correctness is important, not the price per request. Still, an expensive cluster only for this is not wanted.",
             "A cluster that runs all month for 20 million small requests a day is out of proportion."),
        ],
        "scores": {
            "ddb": ["PutItem with the condition attribute_not_exists(pk) (F5): if the id does not exist, it writes and returns \"new\". If it exists, it returns ConditionalCheckFailedException and the application reads the first result. The check and the mark are one atomic step. No points off.",
                    "3,000 requests in single-digit milliseconds, on-demand mode. No points off.",
                    "Each write is stored in several AZs before it is accepted. No points off.",
                    "Serverless. TTL (F6) deletes the marks after 24 hours. No points off.",
                    "Pay per request. 20 million small requests a day is a low bill. No points off."],
            "ec": ["SET id result NX EX 86400 is exactly the same atomic \"write if absent\" operation, and it also sets the expiry in one command. No points off.",
                   "Microseconds. No points off.",
                   "No durable write log. A failure can lose marks, and a repeated request charges the card a second time. 9 points off: on this must requirement a loss is not acceptable, so the candidate is disqualified. (MemoryDB, the in-memory option with a durable log, would get this point.)",
                   "Serverless, EXPIRE. No points off.",
                   "ECPU and GB-hours. 1 point off: minimum fee."],
            "aur": ["INSERT with a UNIQUE constraint: the second request gets a unique violation. The same guarantee. No points off.",
                    "3,000 requests are easy for one writer. 1 point off: the writer size and the connection pool are set in advance.",
                    "Six copies. No points off.",
                    "Managed. 4 points off: for the deletion after 24 hours, a cleanup job (cron or partition drop) is written and operated. The payment team owns a cluster only for this.",
                    "ACU-hours. 4 points off: for a low volume, the minimum capacity is paid all month."],
        },
        "h2h": {
            "ec": "Head to head with in-memory key-value (ElastiCache). Only one requirement differs: R3 durability, and on this card R3 is a must. The SET NX EX command of ElastiCache is the textbook example for idempotency: atomic, one command, with expiry. "
                  "But ElastiCache Serverless has no log that writes each write to disk. A failure can lose the last marks, and each lost mark is a risk of a double charge. The payment team does not take this risk. "
                  "So the durable store of the same category is selected: the conditional PutItem of DynamoDB gives the same atomic guarantee with a durable write. Which condition would make ElastiCache the selection: if the loss of a mark only meant one more retry (for example idempotency for an email). Or: if in-memory speed was necessary and a durable log was wanted. Then not ElastiCache but MemoryDB is selected.",
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R4 and R5. The UNIQUE constraint of Aurora gives the same guarantee. If the payment record is already in a relational database, the strongest solution is to write the mark and the record in the same transaction. Both are written, or none. "
                   "In this workload the payment record is in a separate system of a separate team. An Aurora cluster only for idempotency, a cleanup job for 24 hours, and a minimum capacity all month are out of proportion. "
                   "So the key-value store is selected. Which condition would make Aurora the selection: if the payment record and the mark were in the same database. Then UNIQUE plus a transaction solves the consistency problem between two systems at the root, and that is the best practice.",
        },
        "verdict": "Decision: DynamoDB 50, Aurora 41, ElastiCache disqualified at R3 (40). DynamoDB fully meets each requirement. This use case is the purest example of the conditional write (F5). "
                   "If we still select key-value, our gains: one atomic request, durable, serverless, marks that clean themselves. Our possible losses: the payment record is in another system, so the mark and the record cannot be written in one transaction. The result itself must be written into the value of the mark, and if the record cannot be written, the mark must be deleted. If one condition changed: if the payment record was in the same database, UNIQUE plus a transaction in Aurora would be selected.",
    },

    "seat": {
        "title": "Ticket and seat holds",
        "key": "Key: event, then seat. Value: holder, hold time, expiry.",
        "story": "A ticket site opens the sale of a concert with 20,000 seats. In the first minute, 300,000 people look at the seat map and select seats. A selected seat is held for 10 minutes. If no payment comes, it becomes free again. "
                 "Two people must never hold the same seat. At the start of the sale there are 50,000 hold attempts per second. Five minutes later there are 500 per second. This start happens a few times a year. The team has six developers and a small operations team.",
        "reqs": [
            ("Questions: \"all seats of this event and their status\", \"hold this seat for me only if it is free\", \"release a hold whose time ended\". The hold must be atomic: if two people want the same seat at the same time, exactly one must get it.",
             "A double hold means that the same seat is sold twice. On the night of the concert, this is a scandal that must be solved at the door."),
            ("50,000 hold attempts per second at the start, 500 five minutes later. At the peak, a hold must be accepted in less than 50 milliseconds. The start time is known, but no manual action is wanted at that moment.",
             "The start moment is the reputation of the site. If it is slow, users click the same seat many times and the load multiplies."),
            ("High: a lost hold means that the same seat is sold to a second person. An AZ failure must not lose a hold. On this card, a must.",
             "Until the payment is complete, the hold is the only record of the seat. Its loss is a double sale."),
            ("No capacity plan before the start. Expired holds must become free by themselves. No cleanup job.",
             "If a cleanup job is late, a free seat cannot be sold. If it runs too early, a hold during the payment is deleted."),
            ("Traffic for a few minutes, a few times a year. Low for the rest. Pay for usage.",
             "A system sized for the start is idle for 99.9 percent of the year."),
        ],
        "scores": {
            "ddb": ["Partition key = event, sort key = seat (F3): the seat map is one Query. The hold is an UpdateItem with the condition attribute_not_exists(holder) OR expires_at < :now (F5): if two people race, exactly one wins. 1 point off: an expired hold is not deleted immediately by TTL, so the application must add the time comparison to the condition.",
                    "On-demand mode serves 50,000 requests (F2). 2 points off: all seats of one event are under one partition key. So at the start all traffic goes to one group, that is one partition, and hits the partition limit (1,000 writes per second). The seats must be split into blocks with separate partition keys (EVENT#123#BLOCK#A). This is a design step.",
                    "Each write is stored in several AZs. The conditional write is strongly consistent. No points off.",
                    "Serverless. TTL (F6) deletes an expired hold, and the time comparison in the condition does not wait for the deletion. No points off.",
                    "Pay per request. Almost zero on quiet days. No points off."],
            "aur": ["A row lock with SELECT ... FOR UPDATE, or UPDATE ... WHERE holder IS NULL: a double hold is prevented with certainty. The seat map is one query. No points off.",
                    "50,000 writes per second at the start put a heavy load on one writer. There is lock contention on the rows of the same event. 5 points off: the writer must be moved to the largest class in advance. The limit of 50 ms is still not guaranteed at the peak.",
                    "Six copies. No points off.",
                    "Managed. 4 points off: a cleanup job for expired holds is written, and the writer is enlarged before the start.",
                    "ACU-hours or instance-hours. 4 points off: the capacity enlarged for the start is paid for nothing for the rest of the year. Or it is changed by hand at each start."],
            "ec": ["SET seat holder NX EX 600: an atomic hold and an exact release in one command. The seat map is a hash. 1 point off: the condition \"if free or expired\" is natural with NX. But if the seat status and the hold are two separate keys, a script is necessary for consistency.",
                   "Microseconds. Serverless scales. No points off.",
                   "No durable write log. In a failure, the holds are lost and seats are sold a second time. 9 points off: disqualified on a must requirement.",
                   "Serverless, EXPIRE. No points off.",
                   "ECPU and GB-hours. 2 points off: minimum fee."],
        },
        "h2h": {
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R2 and R5. The row lock of Aurora prevents a double hold in the best-known way. If the sales system (seat, order, payment) is already relational, the hold is written in the same transaction. "
                   "The difference is at the start moment. 50,000 writes per second go to one writer, and locks on the rows of the same event wait for each other. In DynamoDB the write is conditional and has no lock, and it spreads over partitions. The price of DynamoDB is the hot partition design: if the seats are not split into blocks, the start moment overloads one partition. "
                   "In this workload the key-value store is selected, because the start moment decides. A store with no sizing and pay per request is the most economical for a peak of a few minutes a few times a year. Which condition would make Aurora the selection: if the start traffic stayed at a few thousand writes per second. Or: if the hold, the order and the payment had to be written in one transaction. Then the row lock is the simplest and the best solution.",
            "ec": "Head to head with in-memory key-value (ElastiCache). The requirement where they differ: R3 durability, and on this card it is a must. The SET NX EX command of ElastiCache looks almost ideal for a seat hold: atomic, fast, exact expiry. "
                  "But until the payment is complete, the hold is the only record of the seat. In a store with no durable log, a failure loses those records, and each lost hold is a double sale. So the durable key-value store is selected, and instead of an exact expiry, a time comparison is added to the condition. "
                  "Which condition would make ElastiCache the selection: if the hold was also written as a durable record in another place. And: if the one here was only a fast lock. Or: if a durable log was wanted and in-memory speed was necessary (MemoryDB).",
        },
        "verdict": "Decision: DynamoDB 47, Aurora 37, ElastiCache disqualified at R3 (38). The conditional write and the scale per request are the exact match of this workload. "
                   "If we still select key-value, our gains: the start moment is served by itself. The hold rule is one atomic request. Release by expiry. Almost zero cost on quiet days. "
                   "Our possible losses: if the seats of one event are not split into blocks, the start moment makes a hot partition. The expiry is not exact, so a time comparison is added to the condition. The hold, the order and the payment are not in one transaction. If one condition changed: with a low start traffic and a relational sales system, Aurora would win.",
    },

    "rate": {
        "title": "Rate limits and counters",
        "key": "Key: user id and minute. Value: a counter.",
        "story": "An API gateway permits 100 requests per minute for each user. Each request increases the counter. If the new value goes above 100, the request is rejected. The counter has no value after the minute ends. "
                 "20,000 increments per second, at every hour of the day. The counter check is in front of each API request: 2 ms of latency adds 2 ms to each request. A lost counter means 100 extra requests for one minute. The platform team prefers serverless.",
        "reqs": [
            ("\"Increase the counter of this user for this minute by 1 and return the new value\" in one atomic step. If two requests come at the same time, both must be counted. The counters of old minutes must delete themselves.",
             "If the increment is not atomic, two requests read the same value, both write +1, and one is lost: the limit is broken."),
            ("20,000 increments per second, flat. Each increment in less than 2 ms, because it is in front of each API request. On this requirement the latency limit is strict.",
             "The counter is a latency that is added to each request. The difference between 2 ms and 8 ms, on 1.7 billion requests a day, is hours in total."),
            ("Low: a lost counter means 100 extra requests for one minute. It is harmless.",
             "A rate limit is a protection shield, not an accounting record. A gap of one minute is accepted."),
            ("Platform team, prefers serverless, no servers. The counter logic must be a few lines in the gateway code.",
             "The gateway is the code that changes most. If the counter is complex, each change carries risk."),
            ("Each increment is a write: 20,000 writes per second, 52 billion a month. The price per write is the whole cost of this workload.",
             "52 billion writes a month: a small difference in the price of a write unit is tens of thousands of dollars a month."),
        ],
        "scores": {
            "ddb": ["UpdateItem ADD count :one with ReturnValues = UPDATED_NEW is one atomic increment (F5). The minute added to the key (C00001#2026-10-28T14:05) makes each minute a separate value, and TTL (F6) deletes the old minutes. 1 point off: the TTL deletion is late, but because an old minute is never read again, this is only a storage cost.",
                    "20,000 writes are served in on-demand or provisioned mode (F2). 5 points off: the latency is single-digit milliseconds, above the limit of 2 ms. In front of each API request, this difference is felt. DAX does not help writes.",
                    "Durable. No points off. The requirement is low, but it is fully met.",
                    "Serverless, a few lines of SDK. No points off.",
                    "Each increment is one write unit: 52 billion write units a month, clearly more expensive than an in-memory store, also in provisioned mode. 6 points off: the whole of this workload is writes, and a write is the most expensive operation of DynamoDB."],
            "ec": ["INCR key is one atomic increment and returns the new value. With EXPIRE 60, the key is gone exactly at the end of the minute. These commands exist exactly for this task. No points off.",
                   "Microseconds from memory. Serverless scales. No points off.",
                   "No durable log. A failure resets the counters, and the limit is loose for one minute. 4 points off: loss is possible. Here it is harmless.",
                   "Serverless. Two commands. No points off.",
                   "Per ECPU. 20,000 small increments are the cheapest class of workload in an in-memory store, and the data is small. No points off."],
            "aur": ["UPDATE counters SET n = n + 1 WHERE ... RETURNING n is atomic. 1 point off: a deletion job is necessary for old minutes.",
                    "20,000 small writes per second make lock contention and WAL load on one writer. 2 ms in front of each request cannot be guaranteed. 9 points off: disqualified on a must requirement.",
                    "Six copies. No points off.",
                    "Managed. 4 points off: writer sizing and a cleanup job.",
                    "A large writer for continuous high writes is paid all month. 8 points off: the most expensive option for this workload."],
        },
        "h2h": {
            "ec": "Head to head with in-memory key-value (ElastiCache). The requirements where they differ: R2 and R5, and both are in favor of ElastiCache. INCR plus EXPIRE is the textbook example for counters and rate limits: atomic, microseconds, exact deletion at the end of the minute. 20,000 increments are the cheapest work of an in-memory store. "
                  "DynamoDB does the same work atomically with ADD, but in single-digit milliseconds, and each increment is paid as a write unit. Because the whole of this workload is writes, the bill is clearly higher. Durability is the only advantage of DynamoDB, and it is not wanted here. "
                  "In this workload the key-value category is the right one, but inside the category the in-memory store is selected. To select DynamoDB is not wrong. It is expensive and slow. Which condition would make DynamoDB the selection: if the counter was quota accounting (usage that is billed monthly) and its loss was not accepted. Or: if the latency limit was 10 ms. Or: if the increment volume stayed at a few hundred per second.",
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R2 and R5. The atomic UPDATE of Aurora does the job, but 20,000 small writes per second block the lock and WAL path of one writer. The limit of 2 ms does not hold at the peak, and a large writer is paid all month for it. "
                   "In this workload the strength of a relational database (JOIN, transactions, reports) is not used at all. Only its price is paid. Which condition would make Aurora the selection: if the counters were updated in the same transaction as the billing records. And: if the volume stayed at a few hundred per second.",
        },
        "verdict": "Decision: ElastiCache 46, DynamoDB 38, Aurora disqualified at R2 (28). A clear loss. DynamoDB can carry the workload. But the strict latency limit of R2 and the write volume of R5 put the in-memory store far in front. "
                   "If we still select DynamoDB, our gains: the counter is durable and serverless. The team uses the same SDK as for the other tables. If it becomes quota accounting, the design does not change. "
                   "Our possible losses: each request is a few milliseconds slower. The bill for 52 billion write units a month is many times that of the in-memory store. If one condition changed: if the loss of the counter was not accepted and the latency limit was looser, DynamoDB would move in front.",
    },

    "files": {
        "title": "Metadata of files",
        "key": "Key: owner, then folder and file name. Value: size, status, tags, storage location.",
        "story": "In a document application, users upload files. The file itself goes to S3. The application lists the files of each user folder by folder, and shows the status (uploading, ready, deleted), the size and the tags. "
                 "Ten million users, 5 to 5,000 files per user. 5,000 list reads and 500 metadata writes per second, with a peak in working hours. A list must open in less than 100 ms. If the metadata is lost, the file stays in S3, but the user cannot find it. The product team knows the AWS SDK and does not want servers.",
        "reqs": [
            ("Three questions. All files of this user, sorted by folder and name. Only the files of this user in folder X. Move the status of this file from uploading to ready. The user id is known on each request. Users are independent. The fields of a file record differ by type (resolution for an image, page count for a document).",
             "The list screen is the main screen of the application. If a status change happens in the wrong order (ready, then uploading), the user thinks that the file is lost."),
            ("5,000 reads and 500 writes per second. Peak in working hours, low at night. A list in less than 100 ms. Even 5,000 files of one user must open in one list (with pages).",
             "To read a list of 5,000 files one by one takes more than 100 ms. The list must be one sorted read."),
            ("High: if the metadata is lost, the file stays in S3 but the user cannot find it. For the user this is a loss. An AZ failure must not lose data.",
             "The metadata is the address of the file. When the address is lost, the file does not exist in practice."),
            ("Product team, knows the AWS SDK, no servers. No migration for a new file type. Search (by name, by tag) will go to a search service later, and each change of the metadata must flow there.",
             "If the application code feeds the search index, each write path is split in two, and a forgotten path makes the index old."),
            ("Regular traffic. Both payment models are possible. The metadata is small (less than 1 KB per file), but 10 million users x 200 files on average = 2 billion records.",
             "2 billion small records: the storage price per GB and the read price per record decide together."),
        ],
        "scores": {
            "ddb": ["Partition key = user, sort key = FOLDER#file (F3). All files are one sorted Query. Folder X is a begins_with slice. 5,000 files are read in pages. The status change holds in one write with the condition status = :from (F5). The fields differ by type (F4). 1 point off: \"sorted by name, independent of the folder\" is a second order, and that is an LSI or a GSI (F7).",
                    "Reads spread over partitions by user (F2). For 2 billion records nothing changes. No points off.",
                    "Each write is stored in several AZs, point-in-time recovery. No points off.",
                    "Serverless, the SDK that the team knows, no migration. The change stream (F8, Streams in B5) sends each metadata change to the search service (there is also a zero-ETL integration to OpenSearch). No points off.",
                    "2 billion x 1 KB = 2 TB. Pay per GB of storage and per request. 1 point off: a read of a list of 5,000 files uses many read units. For large users, the page size and a projection must limit the cost."],
            "aur": ["An index on (owner, folder, name) gives the same list and the folder slice. A second index by name is one line. The status change is UPDATE ... WHERE status = 'uploading'. When relations such as sharing are added, a JOIN is ready. No points off.",
                    "5,000 reads with readers and 500 writes with one writer are easy. 2 points off: in a table of 2 billion rows, the index size and the vacuum maintenance grow. The team selects the number of readers.",
                    "Six copies. No points off.",
                    "Managed. For the flow to the search service, Aurora zero-ETL or CDC is set up. 3 points off: a field for a new file type needs a schema change (or JSONB). Instance and index maintenance are tasks of the team.",
                    "Instance or ACU-hours plus storage. 3 points off: at night with low traffic you also pay the capacity. The indexes of a 2 TB table multiply the storage."],
            "doc": ["File metadata is a natural document. A compound index on (owner, folder, name) gives the list and the slice. A search in the tag array is possible with a multikey index. The status change is an updateOne with a filter. No points off.",
                    "Reads scale with replicas. 3 points off: for 2 billion documents, the instance and the index memory are sized. All writes go through one primary.",
                    "Six copies. No points off.",
                    "The schema is free. Change streams feed the search service. 3 points off: cluster sizing and the MongoDB API are new for the team.",
                    "Instance per hour plus storage plus I/O. 3 points off: the instances also run in low traffic."],
        },
        "h2h": {
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R2, R4 and R5. The strength of Aurora shows when the metadata grows with other relations: sharing (\"the users who see this file\"), a folder tree, a version history. These are one query with a JOIN. In key-value, each of them is a copy or a second index design. "
                   "The strength of DynamoDB is in scale and in operations: for 2 billion records there is no index maintenance, no vacuum and no instance selection. The list and the folder slice have the same cost at every size. Streams feeds the search service with no code change. "
                   "In this workload the key-value store is selected. The questions are known and independent per user, there are few relations, and the scale is 2 billion records. Which condition would make Aurora the selection: if many-sided relations such as sharing, permissions and a folder tree were the main feature. Or: if reports (\"the 100 users with the most storage\") were asked often. Then the relational model and SQL answer these questions directly.",
            "doc": "Head to head with document (DocumentDB). The requirements where they differ: R2, R4 and R5. In R1 DocumentDB is as good as DynamoDB. In a search in the tag array (multikey index) and in nested metadata updates, it is even more natural. "
                   "The difference is at the scale of 2 billion records and in operations. In DocumentDB, the team selects the instance, the index memory and the number of replicas, and all writes go through one primary. In DynamoDB these decisions do not exist. The team does not know the MongoDB API. "
                   "So the key-value store is selected. Which condition would make DocumentDB the selection: if flexible queries on tags and nested metadata were the main access pattern. Example: \"my documents with the tag invoice and more than 10 pages\". And: if no search service was wanted. Then the document database answers these questions with one index, and no separate search system is necessary.",
        },
        "verdict": "Decision: DynamoDB 48, Aurora 42, DocumentDB 41. The access patterns are known, the users are independent, and the scale is large. These three together are the home ground of key-value. "
                   "If we still select key-value, our gains: the list and the folder slice are cheap at every size. No maintenance for 2 billion records. Durable metadata. The change stream feeds the search service. "
                   "Our possible losses: questions on the content of the value, such as \"all my files with the tag invoice\", need a GSI. Or they go to the search service. Sharing is a two-sided relation and is kept as two copies. Lists of 5,000 files must be read in pages. If one condition changed: if sharing and permission relations were the main feature, Aurora would win.",
    },

    "ads": {
        "title": "Ad and recommendation lookups",
        "key": "Key: user id. Value: a precomputed list of 50 products.",
        "story": "The recommendation model of an e-commerce site computes a list of 50 products for each user every night. When the home page opens, this list is read and shown in the section \"for you\". "
                 "The computation is a batch job at 02:00, 30 minutes long: 20 million writes for 20 million users. During the day there are only reads: 100,000 per second. If the list does not come within 5 ms, the page does not wait and shows a general list. A lost list is computed again tomorrow. The data team knows batch jobs and does not want servers.",
        "reqs": [
            ("One question: \"the list of this user\". The list is one value (50 product ids, 2 KB). Batch writes at night, only reads during the day. There is no query by list content.",
             "The home page opens with this read. The question is one and simple, and the model must be too."),
            ("100,000 reads per second during the day, with a strict limit of 5 ms. Above the limit, the page shows the general list. The recommendation is wasted. 20 million writes in 30 minutes at night, that is 11,000 writes per second. Zero writes during the day.",
             "When the latency limit is exceeded, the recommendation is not shown, and all the work of the model is wasted. The write window at night is narrow: if it does not end in 30 minutes, old lists stay in the morning."),
            ("Low: the list is computed again every night. If it is lost, the general list is shown for one day.",
             "Derived data. Its source is the model, and it is produced again tomorrow."),
            ("The data team knows batch jobs and the AWS SDK, no servers. No separate resize job for the batch write at night.",
             "To increase the capacity by hand each night and to decrease it each morning is not sustainable. It must be automatic."),
            ("Reads are very high and flat. The price per read decides. 20 million x 2 KB = 40 GB of data. The write cost at night is calculated separately.",
             "8.6 billion reads a day: the price of a read unit is the bill of this workload."),
        ],
        "scores": {
            "ddb": ["Simple primary key = user id. The list is one value, and GetItem is one read (F1). Each night each value is overwritten with PutItem (A6: existing key, the full value). BatchWriteItem writes in groups of 25. No points off.",
                    "100,000 reads spread over partitions (F2). 11,000 writes at night are served with on-demand mode or scheduled auto scaling. 2 points off: single-digit milliseconds are close to the limit of 5 ms, and some reads can exceed it. With DAX, reads go to microseconds, but DAX is a separate cluster.",
                    "Durable. No points off.",
                    "Serverless. For the write at night, scheduled auto scaling or on-demand. No points off.",
                    "8.6 billion read units a day (an eventually consistent read of a 2 KB value is 1 unit), paid with provisioned plus reserved capacity. 4 points off: at this volume, the read unit bill is clearly higher than an in-memory cache. With DAX, the read cost goes down, but the hourly fee of DAX is added."],
            "ec": ["One key per user. GET is one read. At night SET overwrites. No points off.",
                   "Less than 1 ms from memory. The limit of 5 ms is easily met. Serverless scales 100,000 reads, and 11,000 writes at night are no problem. No points off.",
                   "No durable log. In a failure the lists are lost, and the general list is shown for one day. 4 points off: loss is possible. Here it is accepted.",
                   "Serverless. No points off.",
                   "ECPU and GB-hours. A read is the cheapest work of an in-memory store. 3 points off: to keep 40 GB of data in memory is much more expensive per GB-hour than on disk. In this workload the cheap reads largely compensate this cost."],
            "aur": ["Read by primary key, JSONB or array column. 1 point off: the update of 20 million rows at night needs a large transaction or a bulk COPY, and it makes vacuum load.",
                    "For 100,000 reads, many reader instances are necessary, each sized in advance. 6 points off: the limit of 5 ms holds when the readers are warm. But during the batch write at night, replica lag and vacuum can slow the reads.",
                    "Six copies. No points off.",
                    "Managed. 4 points off: the reader fleet and the batch write window at night are the planning of the team.",
                    "A reader fleet for 100,000 reads per second is paid per hour. 7 points off: the most expensive option for this workload."],
        },
        "h2h": {
            "ec": "Head to head with in-memory key-value (ElastiCache). The requirements where they differ: R2 and R5 in favor of ElastiCache, R3 in favor of DynamoDB. This workload is the definition of a cache: derived data, only reads during the day, a strict latency limit, loss accepted. "
                  "ElastiCache easily meets the limit of 5 ms and has the lowest cost per read. DynamoDB is near the limit with single-digit milliseconds, and 8.6 billion read units are expensive. The only advantage of DynamoDB is durability, and it is not wanted here. "
                  "The points show DynamoDB one point in front, but the difference is within the margin of error. The best practice is to use both stores together. The lists are written to DynamoDB at night (durable record, easy batch write). During the day DAX or ElastiCache is the cache in front. "
                  "Which condition would make ElastiCache alone the selection: if the memory cost was accepted and the loss of the lists was really not important. Then the batch writes directly to the cache at night, and DynamoDB is not used at all.",
            "aur": "Head to head with relational (Aurora). The requirements where they differ: R2 and R5. The strength of Aurora would show if the recommendations were queried together with the product catalog and the stock (\"recommended products that are in stock\"). In this workload the list is a precomputed value, and there is no JOIN. "
                   "A reader fleet for 100,000 reads per second and a batch update of 20 million rows at night are necessary. This makes Aurora the most expensive option with the most maintenance for this task. Which condition would make Aurora the selection: if the recommendation list was filtered in the same query as the catalog and the stock. And: if the read volume stayed at a few thousand per second.",
        },
        "verdict": "Decision: DynamoDB 44, ElastiCache 43, Aurora 32. A difference of one point is not a decision. In this workload the right answer is \"both together\": the durable list in DynamoDB, the hot reads in DAX or ElastiCache. "
                   "If we still select DynamoDB alone, our gains: durable, serverless. The capacity for the batch write at night and for the reads during the day is set separately. Microseconds are possible with DAX. "
                   "Our possible losses: the limit of 5 ms is close to single-digit milliseconds, and some reads can exceed it. The bill for 8.6 billion read units is higher than an in-memory cache. If one condition changed: if the loss of the lists was really not important and the memory cost was accepted, ElastiCache alone would be selected.",
    },
}
