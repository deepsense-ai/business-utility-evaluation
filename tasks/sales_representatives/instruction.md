# Sales Representatives

The company sells products directly to a chain of stores with locations of various sizes across the country and employs sales representatives. They build relationships with stores and ensure:

- product availability on shelves (to ensure orders arrive on time, avoid shortages, etc.)
- display (arranging products, competing for better shelf space, setting up displays, advertising materials, etc.)
- product placement in the store (at the checkout, at the end of the aisle, at eye level, etc.)
- implementation of the product placement plan/scheme

They also report data on the above, as well as on promotions, competition, and details of their store visits.

Sales depend on many factors, including, of course, those influenced by representatives, but also:
- store type/size
- traffic
- store location
- competitor activities
- price, promotions, etc.

In addition to the data collected by the representative, we also receive data from stores regarding orders and daily sales.

Based on sales results, identify which sales representatives are significantly underperforming in terms of their work efficiency.

Dataset:
- The generated CSV files are available directly in `/app/`.

Answer format:
- Write your final answer to `/app/answer.json`.
- The file must contain only a JSON object with IDs (rep_id) of those representatives taken from the sales_rep data.
- The representative IDs must be sorted ascending.

Example:
```json
{"answer": [1, 2, 3]}
```


