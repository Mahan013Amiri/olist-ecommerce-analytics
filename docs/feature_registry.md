# Feature Registry

> Documentation only — not an execution engine.
> Before using any feature in a predictive model, check **Available At** and **Forbidden Tasks**.

| Feature | Entity / Grain | Available At | Allowed Tasks | Forbidden Tasks |
|---|---|---|---|---|
| `delivery_delay_days` | order | post_delivery | satisfaction, seller_analysis | delivery_delay_prediction, repeat_purchase |
| `order_total_value` | order | order_approved_at | delivery_delay_prediction, analytics | — |
| `order_item_count` | order | order_approved_at | delivery_delay_prediction, analytics | — |

<!-- New features will be added in Task 1.4 (common_features) and later tasks -->
