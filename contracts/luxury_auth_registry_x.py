# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
from dataclasses import dataclass
import json

try:
    gl.UserError = gl.vm.UserError
except Exception:
    pass


def _addr_str(addr: Address) -> str:
    """Safely format an Address instance into a lowercase hex string."""
    try:
        return addr.as_hex.lower()
    except Exception:
        return str(addr).lower()


def _get_sender() -> Address:
    """Safely obtain transaction sender across GenVM runtime versions."""
    try:
        return gl.message.sender
    except Exception:
        try:
            return gl.message.sender_address
        except Exception:
            raise gl.UserError("Cannot resolve sender address.")


def _safe_transfer(recipient: Address, amount: bigint) -> None:
    """Safely disburse native GEN to an address using official GenLayer SDK pattern."""
    if amount <= bigint(0):
        return
    gl.get_contract_at(recipient).emit_transfer(value=u256(int(amount)))


DEFAULT_ALLOWED_DOMAINS = (
    "thewatchregister.com",
    "www.thewatchregister.com",
    "artloss.com",
    "www.artloss.com",
    "stolengoods.org",
    "www.stolengoods.org",
    "watchregister.org",
    "www.watchregister.org",
    "luxuryregistry.org",
    "www.luxuryregistry.org",
    "luxuryauth.org",
    "www.luxuryauth.org",
    "enrico-luxury.com",
    "www.enrico-luxury.com",
    "mock-registry.genlayer.com",
)


def _parse_url_host(raw_url: str) -> str:
    """Extract and validate normalized hostname from URL."""
    clean = raw_url.strip()
    if "?" in clean:
        clean = clean.split("?")[0]
    if "#" in clean:
        clean = clean.split("#")[0]
    clean = clean.strip()

    if clean.startswith("https://"):
        rest = clean[8:]
    elif clean.startswith("http://"):
        rest = clean[7:]
    else:
        raise gl.UserError("URL must begin with http:// or https://")

    host = rest.split("/", 1)[0].strip().lower()
    if ":" in host:
        host = host.split(":")[0].strip()
    if not host:
        raise gl.UserError("Invalid URL: missing host")
    return host


@allow_storage
@dataclass
class LuxuryEscrowDeal:
    deal_id: str
    buyer: Address
    seller: Address
    brand: str               # e.g., "Rolex", "Hermes", "Patek Philippe"
    model: str               # e.g., "Submariner 126610LN"
    serial_number: str       # Unique identifier stamped on the physical luxury item
    registry_lookup_url: str # Authoritative canonical URL for database serial check
    escrow_amount: bigint    # Total purchase price locked
    seller_bond: bigint      # Seller deposit (slashed if stolen/counterfeit)
    status: str              # "FUNDED", "DISPUTED", "SETTLED_TO_SELLER", "REFUNDED_TO_BUYER"
    verdict: str             # "PENDING", "AUTHENTIC_CLEAN", "STOLEN_FLAGGED", "COUNTERFEIT_FLAGGED", "INSUFFICIENT_DATA"
    reason: str              # Consensus explanation
    created_at: bigint
    resolved_at: bigint


class Contract(gl.Contract):
    """
    LuxuryAuthRegistryX: Autonomous Stolen & Counterfeit Luxury Goods Registry & Dispute Arbiter
    Track: Agentic Commerce Infrastructure / Onchain Justice
    """
    owner: Address
    deal_count: bigint
    deals: TreeMap[str, LuxuryEscrowDeal]
    blacklisted_serials: TreeMap[str, bool]
    custom_allowed_domains: TreeMap[str, bool]

    def __init__(self):
        # GenVM automatically initializes TreeMap storage fields to empty.
        # DO NOT iterate/assign collections in __init__ to preserve clean storage initialization.
        self.owner = _get_sender()
        self.deal_count = bigint(0)

    def _parse_llm_json(self, text: str) -> dict:
        """Safely parse LLM responses, stripping markdown wrappers if present."""
        try:
            cleaned = str(text).strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            return json.loads(cleaned.strip())
        except Exception as e:
            return {
                "verdict": "INSUFFICIENT_DATA",
                "confidence": 0,
                "reason": f"Failed to parse LLM JSON: {str(e)[:100]}"
            }

    @gl.public.write
    def add_allowed_domain(self, domain: str) -> None:
        """Owner can allow additional trusted luxury verification domains."""
        if _addr_str(_get_sender()) != _addr_str(self.owner):
            raise gl.UserError("Only owner can add allowed domains.")
        clean = domain.strip().lower()
        if len(clean) < 3:
            raise gl.UserError("Invalid domain name.")
        self.custom_allowed_domains[clean] = True

    @gl.public.write
    def remove_allowed_domain(self, domain: str) -> None:
        """Owner can remove a domain from custom allowed list."""
        if _addr_str(_get_sender()) != _addr_str(self.owner):
            raise gl.UserError("Only owner can remove allowed domains.")
        clean = domain.strip().lower()
        self.custom_allowed_domains[clean] = False

    @gl.public.view
    def is_domain_allowed(self, domain: str) -> bool:
        """Check if a registry domain is whitelisted."""
        clean = domain.strip().lower()
        if clean in DEFAULT_ALLOWED_DOMAINS:
            return True
        return clean in self.custom_allowed_domains and self.custom_allowed_domains[clean]

    @gl.public.write.payable
    def create_and_fund_deal(
        self,
        seller: Address,
        brand: str,
        model: str,
        serial_number: str,
        registry_lookup_url: str
    ) -> str:
        """
        Buyer creates an escrow deal, locking payment value.
        """
        deposit = bigint(gl.message.value)
        if deposit <= bigint(0):
            raise gl.UserError("Escrow payment must be greater than 0 GEN.")

        clean_brand = brand.strip().upper()
        clean_model = model.strip()
        clean_serial = serial_number.strip().upper()
        clean_url = registry_lookup_url.strip()

        if len(clean_brand) < 2 or len(clean_serial) < 4:
            raise gl.UserError("Brand and Serial number must be specific and valid.")

        if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            raise gl.UserError("registry_lookup_url must begin with http:// or https://")

        # Canonical Host Validation (Steward Rule: Canonical Host Binding)
        host = _parse_url_host(clean_url)
        is_allowed = (host in DEFAULT_ALLOWED_DOMAINS) or (
            host in self.custom_allowed_domains and self.custom_allowed_domains[host]
        )
        if not is_allowed:
            raise gl.UserError(f"Registry domain '{host}' is not in the allowed registry whitelist.")

        # Canonical Serial Binding (Steward Rule: Prevent URL spoofing / Replay attacks)
        if clean_serial.lower() not in clean_url.lower():
            raise gl.UserError(f"Registry lookup URL must canonically contain the item serial number '{clean_serial}'.")

        # Fast on-chain check against already known blacklisted serials
        serial_key = f"{clean_brand}:{clean_serial}"
        if serial_key in self.blacklisted_serials and self.blacklisted_serials[serial_key]:
            raise gl.UserError("Serial number is permanently blacklisted on-chain.")

        self.deal_count += bigint(1)
        did = str(self.deal_count)

        self.deals[did] = LuxuryEscrowDeal(
            deal_id=did,
            buyer=_get_sender(),
            seller=seller,
            brand=clean_brand,
            model=clean_model,
            serial_number=clean_serial,
            registry_lookup_url=clean_url,
            escrow_amount=deposit,
            seller_bond=bigint(0),
            status="FUNDED",
            verdict="PENDING",
            reason="Escrow funded by buyer. Waiting for seller bond or delivery.",
            created_at=self.deal_count,
            resolved_at=bigint(0)
        )

        return did

    @gl.public.write.payable
    def deposit_seller_bond(self, deal_id: str) -> None:
        """
        Seller deposits an authenticity bond (guarantee that item is authentic and legally owned).
        """
        if deal_id not in self.deals:
            raise gl.UserError("Deal not found.")

        deal = self.deals[deal_id]
        if deal.status != "FUNDED":
            raise gl.UserError("Deal is not in FUNDED state.")

        if _addr_str(_get_sender()) != _addr_str(deal.seller):
            raise gl.UserError("Only designated seller can deposit bond.")

        bond = bigint(gl.message.value)
        if bond <= bigint(0):
            raise gl.UserError("Bond must be greater than 0 GEN.")

        deal.seller_bond += bond
        self.deals[deal_id] = deal

    @gl.public.write
    def confirm_receipt_and_release(self, deal_id: str) -> None:
        """
        Happy path: Buyer receives item, verifies in person, and releases funds directly.
        """
        if deal_id not in self.deals:
            raise gl.UserError("Deal not found.")

        deal = self.deals[deal_id]
        if _addr_str(_get_sender()) != _addr_str(deal.buyer):
            raise gl.UserError("Only buyer can release escrow directly.")

        if deal.status != "FUNDED":
            raise gl.UserError("Deal is not in FUNDED state.")

        deal.status = "SETTLED_TO_SELLER"
        deal.verdict = "AUTHENTIC_CLEAN"
        deal.reason = "Buyer confirmed direct receipt and satisfaction."
        deal.resolved_at = self.deal_count
        self.deals[deal_id] = deal

        total_seller_payout = deal.escrow_amount + deal.seller_bond
        _safe_transfer(deal.seller, total_seller_payout)

    @gl.public.write
    def dispute_authenticity_or_provenance(self, deal_id: str) -> None:
        """
        Buyer or Seller files an on-chain dispute claiming serial number theft, loss report, or counterfeit.
        Triggers GenLayer AI Jury consensus over the live registry database URL.
        """
        if deal_id not in self.deals:
            raise gl.UserError("Deal not found.")

        deal = self.deals[deal_id]
        if deal.status != "FUNDED":
            raise gl.UserError("Deal is not eligible for adjudication.")

        caller_hex = _addr_str(_get_sender())
        if caller_hex != _addr_str(deal.buyer) and caller_hex != _addr_str(deal.seller):
            raise gl.UserError("Only transaction participants can trigger dispute adjudication.")

        # Extract values to local variables BEFORE nondet block
        brand_local = str(deal.brand)
        model_local = str(deal.model)
        serial_local = str(deal.serial_number)
        lookup_url_local = str(deal.registry_lookup_url)

        def leader_fn():
            web_content = ""
            try:
                res = gl.nondet.web.render(lookup_url_local, mode="text")
                if hasattr(res, "content"):
                    web_content = res.content
                elif isinstance(res, dict) and "body" in res:
                    web_content = res["body"]
                else:
                    web_content = str(res)
            except Exception:
                web_content = ""

            lower_web = web_content[:500].lower() if web_content else ""
            if len(web_content.strip()) < 15 or "404 not found" in lower_web or "access denied" in lower_web:
                return {
                    "verdict": "INSUFFICIENT_DATA",
                    "confidence": 100,
                    "reason": "Registry lookup URL is inaccessible, offline, 404, or blank."
                }

            snippet = web_content[:4000]

            prompt = f"""You are the Decentralized Luxury Goods & Watch Registry Arbiter on GenLayer.
Evaluate whether the following database lookup report indicates that the item with SERIAL NUMBER {serial_local} is reported STOLEN, COUNTERFEIT, or AUTHENTIC/CLEAN.

ITEM DETAILS:
- BRAND: {brand_local}
- MODEL: {model_local}
- SERIAL NUMBER: {serial_local}

DATABASE QUERY RESULT (from {lookup_url_local}):
\"\"\"
{snippet}
\"\"\"

DISCRETE CLASSIFICATION RULES:
Classify into strictly ONE of the following discrete outcomes:
- "STOLEN_FLAGGED": Database explicitly flags this serial number as reported stolen, lost, subject to insurance claim, or theft record.
- "COUNTERFEIT_FLAGGED": Database flags serial number as invalid, duplicate fake, or blacklisted counterfeit.
- "AUTHENTIC_CLEAN": Database confirms serial number is clean, verified, with no negative stolen/loss police records.
- "INSUFFICIENT_DATA": Query result is ambiguous, server error, unrelated search, lacks clear status, or confidence is low.

OUTPUT FORMAT:
Respond ONLY with a VALID JSON object (no markdown, no backticks):
{{
  "verdict": "STOLEN_FLAGGED" | "COUNTERFEIT_FLAGGED" | "AUTHENTIC_CLEAN" | "INSUFFICIENT_DATA",
  "confidence": <integer from 0 to 100>,
  "reason": "<clear explanation max 220 characters>"
}}"""

            try:
                raw_res = gl.nondet.exec_prompt(prompt, response_format="json")
                parsed = None
                if isinstance(raw_res, dict):
                    parsed = raw_res
                elif hasattr(raw_res, "content") and isinstance(raw_res.content, dict):
                    parsed = raw_res.content
                else:
                    text = raw_res.content if hasattr(raw_res, "content") else str(raw_res)
                    cleaned = str(text).strip()
                    if cleaned.startswith("```json"):
                        cleaned = cleaned[7:]
                    elif cleaned.startswith("```"):
                        cleaned = cleaned[3:]
                    if cleaned.endswith("```"):
                        cleaned = cleaned[:-3]
                    parsed = json.loads(cleaned.strip())

                verdict_candidate = str(parsed.get("verdict", "INSUFFICIENT_DATA")).strip().upper()
                valid_verdicts = ("AUTHENTIC_CLEAN", "STOLEN_FLAGGED", "COUNTERFEIT_FLAGGED", "INSUFFICIENT_DATA")
                if verdict_candidate not in valid_verdicts:
                    verdict_candidate = "INSUFFICIENT_DATA"

                try:
                    conf = int(parsed.get("confidence", 0))
                    conf = max(0, min(100, conf))
                except Exception:
                    conf = 50

                # Low confidence falls back to INSUFFICIENT_DATA
                if conf < 70 and verdict_candidate != "INSUFFICIENT_DATA":
                    verdict_candidate = "INSUFFICIENT_DATA"

                reason_str = str(parsed.get("reason", "Serial evaluated by AI registry jury."))[:220]

                return {
                    "verdict": verdict_candidate,
                    "confidence": conf,
                    "reason": reason_str
                }
            except Exception as e:
                return {
                    "verdict": "INSUFFICIENT_DATA",
                    "confidence": 0,
                    "reason": f"Evaluation error: {str(e)[:100]}"
                }

        def validator_fn(leader_res) -> bool:
            if not isinstance(leader_res, gl.vm.Return):
                return False
            leader = leader_res.calldata
            if not isinstance(leader, dict) or "verdict" not in leader:
                return False

            valid_verdicts = ("AUTHENTIC_CLEAN", "STOLEN_FLAGGED", "COUNTERFEIT_FLAGGED", "INSUFFICIENT_DATA")
            l_verdict = str(leader.get("verdict", "")).strip().upper()
            if l_verdict not in valid_verdicts:
                return False

            mine = leader_fn()
            m_verdict = str(mine.get("verdict", "")).strip().upper()

            # DISCRETE EQUIVALENCE: Validators MUST strictly agree on the exact discrete verdict
            return l_verdict == m_verdict

        adjudication_res = gl.vm.run_nondet(leader_fn, validator_fn)
        if isinstance(adjudication_res, dict):
            final_res = adjudication_res
        else:
            final_res = self._parse_llm_json(str(adjudication_res))

        verdict = str(final_res.get("verdict", "INSUFFICIENT_DATA")).strip().upper()
        valid_verdicts = ("AUTHENTIC_CLEAN", "STOLEN_FLAGGED", "COUNTERFEIT_FLAGGED", "INSUFFICIENT_DATA")
        if verdict not in valid_verdicts:
            verdict = "INSUFFICIENT_DATA"

        reason = str(final_res.get("reason", "Consensus concluded."))

        serial_key = f"{deal.brand}:{deal.serial_number}"

        deal.verdict = verdict
        deal.reason = reason
        deal.resolved_at = self.deal_count

        if verdict in ("STOLEN_FLAGGED", "COUNTERFEIT_FLAGGED"):
            # Permanently blacklist serial number on-chain
            self.blacklisted_serials[serial_key] = True

            # Victim protection: Refund buyer 100% of escrow payment + award seller's slashed bond
            total_compensation = deal.escrow_amount + deal.seller_bond
            deal.status = "REFUNDED_TO_BUYER"
            self.deals[deal_id] = deal

            _safe_transfer(deal.buyer, total_compensation)

        elif verdict == "AUTHENTIC_CLEAN":
            # Item provenance verified clean: Release escrow and bond to seller
            total_payout = deal.escrow_amount + deal.seller_bond
            deal.status = "SETTLED_TO_SELLER"
            self.deals[deal_id] = deal

            _safe_transfer(deal.seller, total_payout)

        else:
            # INSUFFICIENT_DATA: Refund buyer their escrow and return bond to seller
            deal.status = "DISPUTED"
            self.deals[deal_id] = deal

            if deal.escrow_amount > bigint(0):
                _safe_transfer(deal.buyer, deal.escrow_amount)
            if deal.seller_bond > bigint(0):
                _safe_transfer(deal.seller, deal.seller_bond)

    @gl.public.view
    def get_deal(self, deal_id: str) -> str:
        """Retrieve details of an escrow deal as a JSON string."""
        if deal_id not in self.deals:
            raise gl.UserError("Deal not found.")
        d = self.deals[deal_id]
        return json.dumps({
            "deal_id": d.deal_id,
            "buyer": _addr_str(d.buyer),
            "seller": _addr_str(d.seller),
            "brand": d.brand,
            "model": d.model,
            "serial_number": d.serial_number,
            "registry_lookup_url": d.registry_lookup_url,
            "escrow_amount": str(d.escrow_amount),
            "seller_bond": str(d.seller_bond),
            "status": d.status,
            "verdict": d.verdict,
            "reason": d.reason,
            "created_at": str(d.created_at),
            "resolved_at": str(d.resolved_at)
        })

    @gl.public.view
    def is_serial_blacklisted(self, brand: str, serial_number: str) -> bool:
        """Check if a specific luxury serial number is blacklisted on-chain."""
        serial_key = f"{brand.strip().upper()}:{serial_number.strip().upper()}"
        return serial_key in self.blacklisted_serials and self.blacklisted_serials[serial_key]

    @gl.public.view
    def get_deal_count(self) -> int:
        return int(self.deal_count)

    @gl.public.view
    def get_owner(self) -> str:
        return _addr_str(self.owner)
