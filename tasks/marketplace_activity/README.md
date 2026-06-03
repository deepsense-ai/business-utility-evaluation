# Marketplace Activity

## Description

This scenario models a company that operates a typical internet marketplace. Users search, browse, click, save listings, create listings, and purchase items. The analytical target is to identify city/category pairs with unexpectedly low transaction activity from the public CSV files.

## Task Design

### Output and Runtime Controls

The main output controls are in `CONFIG["output"]`:

- `csv_split`: either `row_chunk` or `monthly`
- `rows_per_file`: row limit for row-chunk splitting
- `write_simulation_output`: whether to write the human-readable action trace
- `float_rounding`: rounding for floating output fields
- `cleanup_outputs`: whether to delete managed prior outputs before generation

The main simulation scale controls are:

- `CONFIG["scale"]["n_users"]`
- `CONFIG["simulation_days"]`
- `CONFIG["scale"]["min_initial_listings_per_leaf_category"]`
- per-user-group probabilities and ranges
- listing expiration days
- low-activity multipliers

The hidden target signal is configured in `CONFIG["low_activity"]["city_category_names"]`. The configuration of this part is what mainly allows one to make this task easier/more difficult by manipulating the data itself.

### Expected Solution Approach

The intended inference path is to compare demand and engagement by city/category while accounting for:

- user count by city
- listing count by category and city
- searches and results count
- impressions
- click-through rate
- favorite rate
- purchase rate
- sell-through speed
- listing expiration
- differences between similar cities or similar category supply

## Generation

### Local Generation

From the repository root:

```bash
MARKETPLACE_ACTIVITY_OUTPUT_DIR=/tmp/marketplace-activity-out \
uv run python harbor/tasks/marketplace_activity/environment/generate.py
```

To also write the hidden answer locally for debugging, set `MARKETPLACE_ACTIVITY_ANSWER_PATH` before running the generator.

The generator also prints and writes total generation runtime at the end of a successful run.

### Generated Outputs

Only the domain tables from the marketplace schema are written as CSV files:

- `user_001.csv`
- `category_001.csv`
- `listing_*.csv`
- `search_event_*.csv`
- `impression_event_*.csv`
- `click_event_*.csv`
- `favorite_event_*.csv`
- `purchase_*.csv`

The static tables are written once:

- `user_001.csv`
- `category_001.csv`

The event and listing tables are split by the output mode in `CONFIG["output"]["csv_split"]`:

- `row_chunk`: files are split after `CONFIG["output"]["rows_per_file"]` rows, for example `impression_event_001.csv`, `impression_event_002.csv`, and so on.
- `monthly`: files are split by simulation month.

The current default is row chunks with 25,000 rows per file.

Action-level records such as `LISTING_CREATE`, `SEARCH`, `IMPRESSION`, `CLICK`, `FAVORITE`, and `PURCHASE` are not written as public CSV tables. They are written only to `additional/simulation_output.txt` when `CONFIG["output"]["write_simulation_output"] = True`.

## Data Model

### Public Schema

The public dataset follows this marketplace schema:

- `USER`: public account information, including `user_type`, city, registration date, average session time, and active flag
- `CATEGORY`: parent and leaf listing categories
- `LISTING`: listings created by seller users
- `SEARCH_EVENT`: searches performed by users
- `IMPRESSION_EVENT`: listings shown to users after searches
- `CLICK_EVENT`: clicks on displayed listings
- `FAVORITE_EVENT`: saved listings
- `PURCHASE`: completed purchases

### Hidden Data

The generator maintains private fields that influence simulation behavior but are not exported to public CSVs:

- hidden behavioral user segment, such as `casual_browser` or `intent_buyer`
- hidden seller category pools
- collector focus category
- user location kind, city activity factor, and daily session probability
- listing market fit, visibility score, click affinity, and quality segment
- listing sold state and sale timestamp
- low-activity city/category mapping

These hidden fields are used only to generate realistic public behavior. The downstream task is to infer the answer from the public outputs.

## Simulation Mechanics

### Simulation Setup

Default scale is controlled by the top-level `CONFIG` in `generation/generate.py`:

- 180 simulated days starting on `2025-01-01`
- 10,000 users
- at least 20 configured cities
- at least 50 leaf listing categories
- parent categories including Fashion, Electronics, Home, Leisure, Vehicles, Family, Sports, and Services
- most users assigned to cities
- a small number of users assigned to villages, with at most one user per village

### User Groups

Users are assigned to hidden behavior groups according to `CONFIG["user_groups"]`. Each group controls activity rate, session length, search behavior, impression depth, click rate, favorite rate, purchase rate, price sensitivity, and seller behavior.

The hidden behavior groups are:

- `casual_browser`: generates browsing, impressions, and clicks, but buys rarely
- `intent_buyer`: searches with a goal, sees fewer listings, and has a high purchase probability
- `bargain_hunter`: searches more deeply, likes cheap items, favorites often, and buys at a medium rate
- `impulse_buyer`: has high click-through behavior, makes quick decisions, and prefers cheap products
- `collector_enthusiast`: focuses on one category, revisits saved listings, and monitors new listings
- `power_seller`: creates many listings and has high seller activity
- `casual_seller`: creates occasional listings
- `professional_seller`: creates regular listings, uses optimized pricing, and has business-style account labels
- `inactive_dormant`: has no activity

Inactive users are excluded from session simulation. They do not generate listings, searches, impressions, clicks, favorites, or purchases.

The public `user_type` column is generated from `CONFIG["public_user_type_mix_by_behavior"]`. This intentionally hides the behavioral segment.

For example, a `professional_seller` is likely to appear as `business`, while an `impulse_buyer` is likely to appear as `regular`. The public labels are useful account metadata, but they should not directly reveal the hidden simulation profile.

### Locations

Users are concentrated in large cities according to `CONFIG["locations"]["city_weights"]`. Each city also has a `city_activity_factor` that affects how often users from that city enter sessions.

Village users are rare and are sampled without replacement from `CONFIG["locations"]["villages"]`. This keeps the maximum at one user per village. Village activity is also reduced by `village_activity_factor_range`.

City-level activity differences are important: they create realistic differences in marketplace volume even before the hidden low-activity city/category effects are applied.

### Categories

Categories are generated as a parent/leaf tree from `CONFIG["catalog"]["category_tree"]`. Parent rows and leaf rows are both exported to `category_001.csv`.

Only leaf categories receive listings and searches. Each leaf category receives:

- a price range inherited from its parent category
- a sampled base price
- a search weight
- a seller supply weight
- a cheapness score used by price-sensitive users

Category names are intentionally short to keep the CSV files lightweight.

### Listings

Listings are created by seller-capable users. There are two listing creation phases:

- initial listings on the first simulation day
- daily seller listing creation on later days

Initial listing seeding also ensures every leaf category has at least `CONFIG["scale"]["min_initial_listings_per_leaf_category"]` listings.

Each listing includes public fields:

- `listing_id`
- `seller_id`
- `category_id`
- `title`
- `price`
- `condition`
- `created_at`
- `expires_at`

Titles are intentionally simple synthetic phrases. Brand and company names are not used.

Listing price is based on:

- category base price
- condition multiplier
- seller price strategy
- lognormal random noise
- category price bounds

Listing quality is hidden. It is sampled as one of:

- hot
- normal
- weak

This hidden quality affects `market_fit`, `visibility_score`, and `click_affinity`. Hot listings tend to receive more impressions, clicks, favorites, and purchases, while weak listings can remain unsold despite comparable prices.

Unsold listings automatically expire after `CONFIG["listing_model"]["listing_expiration_days"]`, currently 60 days. Expired listings are removed from active search and impression candidate pools. Sold listings are also removed.

### Seller Behavior

Seller-capable users receive hidden category pools. When they create listings, the category is sampled from their pool.

Seller behavior differs by group:

- power sellers list often and in larger batches
- casual sellers list occasionally
- professional sellers list regularly and use the `optimized` price strategy

Seller profiles can also apply visibility multipliers through `seller_visibility_multiplier`.

### Session Simulation

The simulation proceeds day by day. For each day:

1. Seller agents may create new listings.
2. Active user agents are sampled for sessions.
3. Each selected user performs one or more searches.
4. Search results generate impressions.
5. Impressions may generate clicks.
6. Clicks may generate favorites.
7. Clicks may generate purchases.

One simulation step is a user action in the optional human-readable trace. The public CSV tables store the resulting domain records, not the raw hidden action objects.

Daily session selection is based on:

- hidden user active flag
- daily session probability
- city activity factor
- weekday multiplier

### Search Mechanics

For each search, the user chooses a category.

Category choice is affected by:

- category search weight
- user parent-category affinity
- user cheapness preference
- seller category pool, for seller users
- collector focus category, for collector/enthusiast users
- low-activity category selection multiplier, if configured

The search query is short and synthetic. Examples include a category keyword, a `cheap` query for bargain hunters, or a `deal` query for impulse buyers.

The `results_count` in `search_event` is the number of active, visible, unsold, unexpired listings in that category at the search timestamp.

### Impression Mechanics

After a search, the simulator selects a limited number of listings to display.

The number of impressions depends on the hidden user group's `impressions_per_search` range. If the user's city/category pair is configured as unexpectedly low activity, the requested impression count is multiplied by `CONFIG["low_activity"]["impression_multiplier"]`.

Candidate listing weights are based on:

```text
listing_weight =
    visibility_score
    * recency
    * price_score ** 0.55
    * local_listing_bonus
    * own_listing_multiplier
    * seller_city_low_multiplier
```

Where:

- `visibility_score` is hidden listing quality and seller visibility
- `recency` decays with listing age using `recency_half_life_days`
- `price_score` rewards cheaper listings for price-sensitive users
- `local_listing_bonus` rewards listings from the same city as the user
- `own_listing_multiplier` strongly reduces a seller seeing their own listing
- `seller_city_low_multiplier` can reduce visibility for listings from configured low-activity city/category combinations

Collector/enthusiast users may revisit their favorited listings. These impressions use `source_type = favorite_revisit`. Other source types include `search_results`, `category_feed`, `recommended`, `saved_search`, and `new_listing_alert`.

### Weighted Top-k Sampling

Listing impression selection uses weighted sampling without replacement. The vectorized implementation uses the Gumbel top-k trick:

```text
score_i = log(weight_i) + Gumbel(0, 1)
```

The simulator selects the listings with the highest sampled scores. This gives higher-weight listings a better chance of appearing while still allowing randomness and variety.

The implementation uses NumPy arrays for listing fields and `np.argpartition` for top-k selection so it does not fully sort every candidate list.

### Click, Favorite, and Purchase Mechanics

Click probability is computed from:

```text
click_probability =
    base_user_click_probability
    * position_factor
    * click_affinity
    * price_score ** 0.35
    * low_activity_click_factor
```

Position factor decreases for lower-ranked impressions. Own-listing clicks are strongly downweighted.

Favorite probability is computed from:

```text
favorite_probability =
    base_user_favorite_probability
    * market_fit
    * price_score ** 0.30
    * low_activity_favorite_factor
```

Purchase probability is computed from:

```text
purchase_probability =
    base_user_purchase_probability
    * market_fit
    * price_score ** 0.75
    * budget_multiplier
    * low_activity_purchase_factor
```

Impulse buyers receive an additional cheap-product multiplier. Users cannot purchase their own listings.

Purchase final price includes a hidden negotiation discount based on behavior type. Shipping cost depends on item price and category, with zero shipping for Services and some high-price Vehicles listings.

When a purchase happens:

- the listing is marked sold
- the listing is removed from future active candidates
- a row is written to `purchase`
- intent and impulse buyers stop browsing for the current session

### Unexpectedly Low Activity Mechanics

For each configured city/category pair, the simulator applies several penalties:

- `category_selection_multiplier`: affects how often users in that city choose the category
- `impression_multiplier`: reduces how many listings they see for that category
- `click_multiplier`: reduces click probability
- `favorite_multiplier`: reduces favorite probability
- `purchase_multiplier`: reduces purchase probability
- `seller_city_visibility_multiplier`: optionally affects visibility of listings whose seller city is in a low-activity city/category pair

This creates city/category combinations with limited engagement even when listings and prices may look comparable to other cities.

## Validation Notes

The generator performs internal checks before finishing:

- public `user_type` values do not reveal hidden behavioral segment names
- inactive users have no generated activity
- villages have at most one user
- at least 20 cities are configured
- at least 50 leaf listing categories are configured
- at least 5 cities have unexpectedly low activity categories
- each low-activity city has at least 3 configured categories
- purchase count matches the number of sold listings
