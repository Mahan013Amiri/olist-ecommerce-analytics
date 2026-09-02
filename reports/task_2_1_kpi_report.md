# Task 2.1 — KPI Report

Every KPI below states its exact denominator — no rate is computed over an implicit or ambiguous base.

| kpi_name                 |        numerator |     denominator |    value | denominator_definition                              |
|:-------------------------|-----------------:|----------------:|---------:|:----------------------------------------------------|
| delivery_delay_rate      |   6534           | 96470           |   0.0677 | eligible delivered orders (has delivery_delay_days) |
| on_time_delivery_rate    |  89936           | 96470           |   0.9323 | eligible delivered orders (has delivery_delay_days) |
| avg_delivery_delay_days  |     -1.14567e+06 | 96470           | -11.8759 | eligible delivered orders (has delivery_delay_days) |
| avg_delay_of_late_orders |  69392           |  6534           |  10.6201 | orders where is_delayed == True                     |
| order_completion_rate    |  96478           | 99441           |   0.9702 | all orders                                          |
| order_with_item_rate     |  98666           | 99441           |   0.9922 | all orders                                          |
| canceled_rate            |    625           | 99441           |   0.0063 | all orders                                          |
| freight_to_value_ratio   |      2.25191e+06 |     1.35916e+07 |   0.1657 | sum(order_total_value) over orders with items       |
| avg_review_score         | 398296           | 95832           |   4.1562 | delivered orders with a non-null review_score       |
