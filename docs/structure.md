# Structure
The structure of the Portfolio Class is based on a few key principles and is expanded from there.

## Tables
<details><summary>transaction</summary>

| field      | required |
| ---------- | -------- |
| date       | Y        |
| ticker     | Y        |
| type       | Y        |
| units      | Y        |
| cost       | Y        |
| broker     | N        |
| sale_price | Y        |
</details>

<details><summary>price history</summary>

| field      | required |
| ---------- | -------- |
| ticker     | Y        |
| date       | Y        |
| last_price | Y        |
</details>

<details><summary>performance</summary>
    
| field            |
| ---------------- |
| date             |
| average_price    |
| last_price       |
| cumulative_units |
| cumulative_cost  |
| market_value     |
| return           |
| return_pct       |
| realized         |
| unrealized       |

</details>


