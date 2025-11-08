# 2026 Draft Compensatory Picks - Quick Reference

## Awarded from 2025 FAAD

### Round 1 Compensatory Picks (5 total)

| Seq | Recipient | Player Signed    | Original Owner         | Txn ID | Current Status |
| --- | --------- | ---------------- | ---------------------- | ------ | -------------- |
| C1  | TJ        | Davante Adams    | TJ (paid to Andy)      | 3814   | TJ owns        |
| C2  | Joe       | Aidan Hutchinson | Joe (paid to Gordon)   | 3815   | Joe owns       |
| C3  | Gordon    | Devonta Smith    | Gordon (paid to Piper) | 3819   | Gordon owns    |
| C4  | Joe       | Garrett Wilson   | Joe (paid to James)    | 3821   | Joe owns       |
| C5  | Jason     | Trey McBride     | Jason (paid to Kevin)  | 3823   | Jason owns     |

**Expected pick numbers**: Will be assigned chronologically during draft (likely P13-P17)

### Round 2 Compensatory Picks (3 total)

| Seq | Recipient | Player Signed   | Original Owner       | Txn ID | Current Status                |
| --- | --------- | --------------- | -------------------- | ------ | ----------------------------- |
| C1  | Andy      | Jaylen Waddle   | Andy (paid to James) | 3822   | Andy owns                     |
| C2  | JP        | Travis Etienne  | JP (paid to Chip)    | 3812   | JP owns                       |
| C3  | Piper     | Patrick Mahomes | Piper (paid to JP)   | 3824   | **TRADED to Eric (Txn 3957)** |

**Expected pick numbers**: Will be assigned chronologically during draft (likely P25-P30)

**Note**: Transaction 3957 shows Piper's R2 comp (from Mahomes) was traded to Eric as pick P30.

### Round 3 Compensatory Picks (1 total)

| Seq | Recipient | Player Signed | Original Owner  | Txn ID | Current Status |
| --- | --------- | ------------- | --------------- | ------ | -------------- |
| C1  | JP        | Jessie Bates  | JP (paid to TJ) | 3809   | JP owns        |

**Expected pick numbers**: Will be assigned chronologically during draft (likely P40)

**Data Quality Note**: Commissioner's draft_picks table incorrectly lists this as a Round 2 comp pick, but FAAD transaction 3809 clearly shows "3rd to JP".

______________________________________________________________________

## Expected 2026 Draft Structure

| Round     | Base Picks | Comp Picks | Total Picks | Pick Range           |
| --------- | ---------- | ---------- | ----------- | -------------------- |
| 1         | 12         | 5          | **17**      | P1-P17               |
| 2         | 12         | 3          | **15**      | P18-P32 (or similar) |
| 3         | 12         | 1          | **13**      | P33-P45 (or similar) |
| 4         | 12         | 0          | **12**      | P46-P57 (or similar) |
| 5         | 12         | 0          | **12**      | P58-P69 (or similar) |
| **TOTAL** | **60**     | **9**      | **69**      |                      |

**Note**: Exact pick numbers for rounds 2-5 depend on comp pick placement within each round.

______________________________________________________________________

## Compensatory Pick Assignment Logic

Based on historical patterns:

1. **Comp picks awarded**: When a team signs a UFA in FAAD, the team that lost the player receives a comp pick in the NEXT year's draft
2. **Round determination**: Based on contract value of player signed
3. **Pick sequencing**: Comp picks appear to be inserted chronologically within their round based on FAAD draft order
4. **Pick number assignment**: Happens after FAAD is complete and final draft order is determined

______________________________________________________________________

## Multiple Comp Picks to Same Owner

**Joe Stanek** has 2 first-round comp picks for 2026:

- C1: Aidan Hutchinson (lost to Gordon)
- C2: Garrett Wilson (lost to James)

This is legal and creates interesting draft capital concentration.

______________________________________________________________________

## Traded Comp Picks

Even before the draft order is finalized, comp picks can be traded:

**Example**: Piper's 2026 R2 comp pick (from Mahomes signing)

- Awarded: 2025 FAAD (Txn 3824) - "2nd to Piper"
- Traded: 2025 Week 8 (Txn 3957) - Piper → Eric
- Current owner: Eric
- Pick designation: 2026 R2 P30

This demonstrates that comp picks enter the tradeable pick pool immediately after being awarded, even before exact pick numbers are assigned (TBD → final number transition).

______________________________________________________________________

## Questions for Further Investigation

1. **Pick numbering**: What is the exact algorithm for assigning final pick numbers to comp picks? Chronological within round by FAAD order?
2. **Contract thresholds**: What contract value triggers which round comp pick?
3. **Multiple comps in one transaction**: If a team loses multiple UFAs to the same team, do they get multiple comps?
4. **Conditional comp picks**: Do these exist? (Similar to NFL conditional comp picks)

______________________________________________________________________

Generated: 2025-11-07
Source: Commissioner transactions table (dt=2025-11-06)
Validation: Cross-referenced with draft_picks table and historical draft results
