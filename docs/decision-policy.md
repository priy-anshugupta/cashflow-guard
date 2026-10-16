# Decision policy

The target behavior follows the challenge contract: protect the user's minimum reserve, essentials, and preferences while comparing available ways to complete the request.

## Cash interpretation

Reserve pending debits. Do not spend pending credits, speculative bonuses, lottery proceeds, or unrealized gains. Recognize confirmed income at settlement. Infer recurring streams only from supporting history. Treat explicit cancellation, settlement, or amendment as stronger evidence than an unamended record.

## Payment candidates

The generator considers full payment, supplied installment schedules, eligible partial payment, waiting, and permitted spending changes. Partial payment requires user acceptance, request support, a positive initial amount smaller than the request, and a second payment by the desired completion date. Installments must follow a supplied option and user preferences.

Candidate ranking prefers completion by the deadline, no spending changes, lower total cost, earlier start, and fewer payments, followed by a stable option identifier tie-breaker. The main pipeline rejects the selected result when it does not complete by the deadline.

## Safety calculation

`calculate_safe_amount` uses the lowest projected reserve cushion before optional changes, clamps the result to the request amount, and rounds to two decimal places. The simulator checks the debit-first intra-day trough, not only the closing balance.

These are implementation rules and design goals, not a proof of full contract compliance. Date-window behavior, floating-point rounding, and heuristic reconstruction require review; see [limitations](limitations.md).
