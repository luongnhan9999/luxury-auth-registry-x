# Portal Submission Draft — LuxuryAuthRegistryX

**Portal Track:** Builder  
**Contribution Type:** Intelligent Contracts  
**Network:** studionet  
**Contract Address:** `0x5290c0d554B3Cf059fF92BE5001080ca8A58a03b`  
**Deployer / Owner:** `0x52c5e913fc54d00cba5df3312268bf66035661f8`  
**Evidence URL:** `https://github.com/luongnhan9999/luxury-auth-registry-x`  

---

### What did you change? (Field on Portal Edit Submission — <1000 chars)

```text
Per Steward review:
1. Updated `deposit_seller_bond`: Strictly enforces `deal.status == "FUNDED"` before accepting funds or mutating state. Reverts with `gl.UserError("Deal is not in FUNDED state.")` if the deal has concluded or transitioned.
2. Exact Line 1 Magic Pragma: Line 1 strictly begins with `# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }` without `# v0.2.16` above it. Removed internal monkey-patches from contract body.
3. Added dedicated regression test `test_deposit_seller_bond_reverts_after_terminal_states` covering all 3 terminal scenarios (settled, refunded, disputed).
4. Verified 100% test pass rate across all 15 unit tests in gltest (~1.8s).
5. Redeployed corrected contract to Studionet at:
   0x5290c0d554B3Cf059fF92BE5001080ca8A58a03b
6. Updated GitHub repository with matching verified source and documentation:
   https://github.com/luongnhan9999/luxury-auth-registry-x
```

---

### Title
LuxuryAuthRegistryX — Autonomous Stolen & Counterfeit Luxury Goods Registry & Dispute Arbiter

### Description (<1000 characters)
LuxuryAuthRegistryX is an autonomous escrow and provenance verification primitive for secondary luxury goods (watches, fine art, designer bags). When authenticity or theft disputes arise, GenLayer validators audit authoritative loss registries (The Watch Register, Art Loss Register) via live web rendering and resolve claims directly on-chain.

Validators enforce semantic agreement on the MEANING of the decision (strictly matching discrete verdicts: AUTHENTIC_CLEAN, STOLEN_FLAGGED, COUNTERFEIT_FLAGGED, INSUFFICIENT_DATA), not superficial JSON syntax. Canonical host and serial binding prevents URL spoofing. Flagged serials are permanently blacklisted on-chain while escrow and slashed seller bonds disburse trustlessly.

Downstream uses: decentralized luxury marketplaces (Chrono24-style), RWA collateralized lending, and peer-to-peer escrow protocols. Ships with 15 gltest unit tests and full docs. Deployed on studionet at 0x5290c0d554B3Cf059fF92BE5001080ca8A58a03b.

