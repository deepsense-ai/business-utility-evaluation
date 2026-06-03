# Marketplace Activity

A company owning an online marketplace wants to better understand supply/demand in its market and run targeted campaigns encouraging users to buy items from a given category. Users are located in different cities. The company is interested in which cities, and for which categories, additional marketing / improved recommendations / free delivery offers, etc., is particularly needed due to the unexpected variability of demand depending on location. They want to find cities where the number of transactions could be further increased using dedicated strategies (such as more notifications like "Buy products from category <X> on our platform!"), as this, for example, is strongly suggested by activity in other cities for the same listing categories.

The question should be answered based on the user activity in different cities. We are interested only in cities with a non-negligible number of users.

We also know that there are different types of users and their behavior depends on which group they belong to. Also, note that according to the company policy, unsold listings automatically expire after 2 months.

Dataset:

- The generated CSV files are available directly in `/app`.

Answer format:

- Write your final answer to `/app/answer.json`.
- The file must contain only a JSON object mapping city names to arrays of category names
- Sort city keys alphabetically.
- Sort category names alphabetically inside each array.

Example:

```json
{"Lyon":["Books","Clothes"],"Paris":["Smartphones"]}
```
