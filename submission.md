# Portal Submission Draft — LuxuryAuthRegistryX

**Portal Track:** Builder  
**Contribution Type:** Intelligent Contracts  
**Network:** studionet  
**Contract Address:** `0xd74B7d80dE90efF7e2325B4c9773712d072f6dC4`  
**Transaction Hash:** `0x1a2447042130fb7ece594b082edf7de6bd4aa7b9844cfa413eaf60c2be5badf3`  
**Evidence URL:** `https://github.com/luongnhan9999/luxury-auth-registry-x`  

---

### What did you change? (Field on Portal Edit Submission — <1000 chars)

```text
Per Steward Joaquin's review request:
1. Updated `deposit_seller_bond`: Now strictly enforces `deal.status == "FUNDED"` before accepting funds or mutating state. Reverts with `gl.UserError("Deal is not in FUNDED state.")` if the deal has concluded or transitioned.
2. Added dedicated regression test `test_deposit_seller_bond_reverts_after_terminal_states` covering all 3 terminal scenarios:
   - Reverts after seller settlement (SETTLED_TO_SELLER)
   - Reverts after buyer refund via stolen/counterfeit adjudication (REFUNDED_TO_BUYER)
   - Reverts after insufficient-data dispute closure (DISPUTED)
3. Verified 100% test pass rate across all 15 unit tests in gltest.
4. Redeployed corrected contract to Studionet at:
   0xd74B7d80dE90efF7e2325B4c9773712d072f6dC4 (Tx: 0x1a2447042130fb7ece594b082edf7de6bd4aa7b9844cfa413eaf60c2be5badf3).
5. Updated GitHub repository with matching corrected source and deployment evidence:
   https://github.com/luongnhan9999/luxury-auth-registry-x
```

---

### Title
LuxuryAuthRegistryX — Autonomous Stolen & Counterfeit Luxury Goods Registry & Dispute Arbiter

### Description (<1000 characters)
LuxuryAuthRegistryX is an autonomous escrow and provenance verification primitive for secondary luxury goods (watches, fine art, designer bags). When authenticity or theft disputes arise, GenLayer validators audit authoritative loss registries (The Watch Register, Art Loss Register) via live web rendering and resolve claims directly on-chain.

Validators enforce semantic agreement on the MEANING of the decision (strictly matching discrete verdicts: AUTHENTIC_CLEAN, STOLEN_FLAGGED, COUNTERFEIT_FLAGGED, INSUFFICIENT_DATA), not superficial JSON syntax. Canonical host and serial binding prevents URL spoofing. Flagged serials are permanently blacklisted on-chain while escrow and slashed seller bonds disburse trustlessly.

Downstream uses: decentralized luxury marketplaces (Chrono24-style), RWA collateralized lending, and peer-to-peer escrow protocols. Ships with 15 gltest unit tests and full docs. Deployed on studionet at 0xd74B7d80dE90efF7e2325B4c9773712d072f6dC4.
