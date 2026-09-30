import pytest
import json
from gltest import *


@pytest.fixture
def contract(direct_deploy):
    return direct_deploy("contracts/luxury_auth_registry_x.py")


def test_initial_state_and_domains(contract, direct_vm, direct_alice, direct_bob):
    assert contract.get_deal_count() == 0
    assert contract.is_domain_allowed("thewatchregister.com") is True
    assert contract.is_domain_allowed("artloss.com") is True
    assert contract.is_domain_allowed("stolengoods.org") is True
    assert contract.is_domain_allowed("watchregister.org") is True
    assert contract.is_domain_allowed("fake-registry.xyz") is False

    # Owner (direct_deploy deployer) adds new allowed domain
    # Default direct_deploy sender is contract.owner
    contract.add_allowed_domain("new-luxury-check.ch")
    assert contract.is_domain_allowed("new-luxury-check.ch") is True

    # Owner removes allowed domain
    contract.remove_allowed_domain("new-luxury-check.ch")
    assert contract.is_domain_allowed("new-luxury-check.ch") is False

    # Non-owner cannot add allowed domain
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only owner can add allowed domains"):
        contract.add_allowed_domain("hacker-domain.com")


def test_create_and_fund_deal_success(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 5000

    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="ROLEX",
        model="Submariner 126610LN",
        serial_number="R123456",
        registry_lookup_url="https://thewatchregister.com/search/r123456"
    )

    assert did == "1"
    assert contract.get_deal_count() == 1
    assert contract.is_serial_blacklisted("ROLEX", "R123456") is False

    deal_json = json.loads(contract.get_deal("1"))
    assert deal_json["deal_id"] == "1"
    assert deal_json["buyer"] == direct_alice.as_hex.lower()
    assert deal_json["seller"] == direct_bob.as_hex.lower()
    assert deal_json["brand"] == "ROLEX"
    assert deal_json["model"] == "Submariner 126610LN"
    assert deal_json["serial_number"] == "R123456"
    assert deal_json["escrow_amount"] == "5000"
    assert deal_json["seller_bond"] == "0"
    assert deal_json["status"] == "FUNDED"
    assert deal_json["verdict"] == "PENDING"


def test_create_deal_validation_failures(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice

    # 1. Zero escrow payment
    direct_vm.value = 0
    with pytest.raises(Exception, match="Escrow payment must be greater than 0 GEN"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Submariner",
            serial_number="R123456",
            registry_lookup_url="https://thewatchregister.com/search/r123456"
        )

    # 2. Short brand
    direct_vm.value = 1000
    with pytest.raises(Exception, match="Brand and Serial number must be specific and valid"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="R",
            model="Submariner",
            serial_number="R123456",
            registry_lookup_url="https://thewatchregister.com/search/r123456"
        )

    # 3. Short serial
    with pytest.raises(Exception, match="Brand and Serial number must be specific and valid"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Submariner",
            serial_number="R1",
            registry_lookup_url="https://thewatchregister.com/search/r1"
        )

    # 4. Invalid URL scheme
    with pytest.raises(Exception, match="registry_lookup_url must begin with http:// or https://"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Submariner",
            serial_number="R123456",
            registry_lookup_url="ftp://thewatchregister.com/search/r123456"
        )

    # 5. Non-whitelisted domain (Canonical Host Rule)
    with pytest.raises(Exception, match="is not in the allowed registry whitelist"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Submariner",
            serial_number="R123456",
            registry_lookup_url="https://fake-luxury-checker.com/check/r123456"
        )

    # 6. Serial Number not in URL (Canonical Serial Binding Rule: Replay / Spoof Prevention)
    with pytest.raises(Exception, match="must canonically contain the item serial number"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Submariner",
            serial_number="R123456",
            registry_lookup_url="https://thewatchregister.com/search/DIFFERENT_SERIAL"
        )


def test_deposit_seller_bond(contract, direct_vm, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    direct_vm.value = 5000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="HERMES",
        model="Birkin 30 Togo",
        serial_number="H998877",
        registry_lookup_url="https://luxuryauth.org/database/h998877"
    )

    # Non-seller cannot deposit bond
    direct_vm.sender = direct_charlie
    direct_vm.value = 1000
    with pytest.raises(Exception, match="Only designated seller can deposit bond"):
        contract.deposit_seller_bond(did)

    # Zero bond fails
    direct_vm.sender = direct_bob
    direct_vm.value = 0
    with pytest.raises(Exception, match="Bond must be greater than 0 GEN"):
        contract.deposit_seller_bond(did)

    # Seller deposits bond successfully
    direct_vm.value = 1000
    contract.deposit_seller_bond(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["seller_bond"] == "1000"


def test_confirm_receipt_and_release_happy_path(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 8000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="PATEK PHILIPPE",
        model="Nautilus 5711/1A",
        serial_number="P571100",
        registry_lookup_url="https://thewatchregister.com/item/p571100"
    )

    # Seller deposits 2000 bond
    direct_vm.sender = direct_bob
    direct_vm.value = 2000
    contract.deposit_seller_bond(did)

    # Non-buyer cannot confirm receipt
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only buyer can release escrow directly"):
        contract.confirm_receipt_and_release(did)

    # Buyer confirms receipt
    direct_vm.sender = direct_alice
    contract.confirm_receipt_and_release(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["status"] == "SETTLED_TO_SELLER"
    assert deal_json["verdict"] == "AUTHENTIC_CLEAN"
    assert "Buyer confirmed direct receipt" in deal_json["reason"]

    # Cannot confirm again
    with pytest.raises(Exception, match="Deal is not in FUNDED state"):
        contract.confirm_receipt_and_release(did)


def test_dispute_authenticity_stolen_flagged(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 10000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="ROLEX",
        model="Daytona 116500LN",
        serial_number="DAYTONA777",
        registry_lookup_url="https://thewatchregister.com/check/daytona777"
    )

    # Seller deposits 2000 bond
    direct_vm.sender = direct_bob
    direct_vm.value = 2000
    contract.deposit_seller_bond(did)

    # Mock web response: Police stolen report
    direct_vm.mock_web("daytona777", {
        "status": 200,
        "body": "The Watch Register Record for DAYTONA777: Stolen in London on 2026-05-12. Active Interpol theft notice."
    })

    # Mock LLM verdict: STOLEN_FLAGGED
    direct_vm.mock_llm(".*", json.dumps({
        "verdict": "STOLEN_FLAGGED",
        "confidence": 98,
        "reason": "Serial is actively flagged in police database as reported stolen."
    }))

    # Buyer files dispute
    direct_vm.sender = direct_alice
    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["status"] == "REFUNDED_TO_BUYER"
    assert deal_json["verdict"] == "STOLEN_FLAGGED"
    assert "stolen" in deal_json["reason"].lower()

    # Verify serial is now permanently blacklisted on-chain
    assert contract.is_serial_blacklisted("ROLEX", "DAYTONA777") is True

    # Attempting to create a new deal with the blacklisted serial MUST REVERT!
    direct_vm.sender = direct_alice
    direct_vm.value = 5000
    with pytest.raises(Exception, match="Serial number is permanently blacklisted on-chain"):
        contract.create_and_fund_deal(
            seller=direct_bob,
            brand="ROLEX",
            model="Daytona 116500LN",
            serial_number="DAYTONA777",
            registry_lookup_url="https://thewatchregister.com/check/daytona777"
        )


def test_dispute_authenticity_counterfeit_flagged(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 6000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="CARTIER",
        model="Santos Medium",
        serial_number="C990011",
        registry_lookup_url="https://watchregister.org/verify/c990011"
    )

    direct_vm.sender = direct_bob
    direct_vm.value = 1500
    contract.deposit_seller_bond(did)

    # Mock web response: Duplicate / counterfeit serial
    direct_vm.mock_web("c990011", {
        "status": 200,
        "body": "WatchRegister Verification: Serial C990011 is identified as duplicate clone manufactured by illicit replica factory."
    })

    direct_vm.mock_llm(".*", json.dumps({
        "verdict": "COUNTERFEIT_FLAGGED",
        "confidence": 95,
        "reason": "Serial flagged as duplicate clone fake by manufacturer alert."
    }))

    direct_vm.sender = direct_bob # Seller can also trigger dispute
    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["status"] == "REFUNDED_TO_BUYER"
    assert deal_json["verdict"] == "COUNTERFEIT_FLAGGED"
    assert contract.is_serial_blacklisted("CARTIER", "C990011") is True


def test_dispute_authenticity_clean_verified(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 7500
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="AUDEMARS PIGUET",
        model="Royal Oak 15500ST",
        serial_number="AP15500CLEAN",
        registry_lookup_url="https://thewatchregister.com/audit/ap15500clean"
    )

    direct_vm.sender = direct_bob
    direct_vm.value = 2000
    contract.deposit_seller_bond(did)

    # Mock web response: Clean certificate
    direct_vm.mock_web("ap15500clean", {
        "status": 200,
        "body": "The Watch Register Search: AP15500CLEAN - Status: No loss or theft recorded. Verified authentic provenance certificate issued."
    })

    # LLM verdict with markdown wrappers
    direct_vm.mock_llm(".*", "```json\n" + json.dumps({
        "verdict": "AUTHENTIC_CLEAN",
        "confidence": 99,
        "reason": "Serial clean and verified authentic with zero adverse records."
    }) + "\n```")

    direct_vm.sender = direct_alice
    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["status"] == "SETTLED_TO_SELLER"
    assert deal_json["verdict"] == "AUTHENTIC_CLEAN"
    assert contract.is_serial_blacklisted("AUDEMARS PIGUET", "AP15500CLEAN") is False


def test_dispute_inaccessible_url_insufficient_data(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 3000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="OMEGA",
        model="Speedmaster Moonwatch",
        serial_number="OMG186100",
        registry_lookup_url="https://thewatchregister.com/check/omg186100"
    )

    # Mock web: 404 Not Found
    direct_vm.mock_web("omg186100", {
        "status": 404,
        "body": "404 Not Found"
    })

    direct_vm.sender = direct_alice
    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["status"] == "DISPUTED"
    assert deal_json["verdict"] == "INSUFFICIENT_DATA"
    assert "inaccessible, offline, 404" in deal_json["reason"]
    # Serial should NOT be blacklisted on insufficient data
    assert contract.is_serial_blacklisted("OMEGA", "OMG186100") is False


def test_dispute_third_party_reverts(contract, direct_vm, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    direct_vm.value = 1000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="BREITLING",
        model="Navitimer B01",
        serial_number="NAV001122",
        registry_lookup_url="https://thewatchregister.com/check/nav001122"
    )

    # Charlie (stranger) attempts to dispute
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="Only transaction participants can trigger dispute adjudication"):
        contract.dispute_authenticity_or_provenance(did)


def test_dispute_non_funded_state_reverts(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 5000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="VACHERON CONSTANTIN",
        model="Overseas 4500V",
        serial_number="VC4500123",
        registry_lookup_url="https://thewatchregister.com/search/vc4500123"
    )

    contract.confirm_receipt_and_release(did)

    with pytest.raises(Exception, match="Deal is not eligible for adjudication"):
        contract.dispute_authenticity_or_provenance(did)


def test_dispute_invalid_llm_json_fallback(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 4000
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="TUDOR",
        model="Black Bay 58",
        serial_number="TUD9900",
        registry_lookup_url="https://thewatchregister.com/search/tud9900"
    )

    direct_vm.mock_web("tud9900", {
        "status": 200,
        "body": "Tudor database check returns internal system message."
    })
    direct_vm.mock_llm(".*", "This is totally not JSON syntax at all.")

    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["verdict"] == "INSUFFICIENT_DATA"
    assert deal_json["status"] == "DISPUTED"


def test_dispute_low_confidence_fallback(contract, direct_vm, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    direct_vm.value = 4500
    did = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="PANERAI",
        model="Luminor Marina",
        serial_number="PAM01312",
        registry_lookup_url="https://thewatchregister.com/search/pam01312"
    )

    direct_vm.mock_web("pam01312", {
        "status": 200,
        "body": "Unclear records found on partial matching string."
    })
    # Confidence is 50 (< 70)
    direct_vm.mock_llm(".*", json.dumps({
        "verdict": "AUTHENTIC_CLEAN",
        "confidence": 50,
        "reason": "Very uncertain report."
    }))

    contract.dispute_authenticity_or_provenance(did)

    deal_json = json.loads(contract.get_deal(did))
    assert deal_json["verdict"] == "INSUFFICIENT_DATA"
    assert deal_json["status"] == "DISPUTED"


def test_multi_deal_isolation(contract, direct_vm, direct_alice, direct_bob):
    # Deal 1: Stolen Rolex
    direct_vm.sender = direct_alice
    direct_vm.value = 8000
    did1 = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="ROLEX",
        model="Submariner",
        serial_number="STOLEN100",
        registry_lookup_url="https://thewatchregister.com/check/stolen100"
    )

    # Deal 2: Clean Patek
    did2 = contract.create_and_fund_deal(
        seller=direct_bob,
        brand="PATEK",
        model="Calatrava",
        serial_number="CLEAN200",
        registry_lookup_url="https://thewatchregister.com/check/clean200"
    )

    assert did1 == "1"
    assert did2 == "2"
    assert contract.get_deal_count() == 2

    # Dispute Deal 1 as stolen
    direct_vm.mock_web("stolen100", {"status": 200, "body": "Serial STOLEN100 confirmed stolen."})
    direct_vm.mock_llm(".*STOLEN100.*", json.dumps({"verdict": "STOLEN_FLAGGED", "confidence": 99, "reason": "Confirmed stolen."}))
    contract.dispute_authenticity_or_provenance(did1)

    # Dispute Deal 2 as clean
    direct_vm.mock_web("clean200", {"status": 200, "body": "Serial CLEAN200 authentic and clean."})
    direct_vm.mock_llm(".*CLEAN200.*", json.dumps({"verdict": "AUTHENTIC_CLEAN", "confidence": 99, "reason": "Confirmed clean."}))
    contract.dispute_authenticity_or_provenance(did2)

    deal1 = json.loads(contract.get_deal(did1))
    deal2 = json.loads(contract.get_deal(did2))

    assert deal1["verdict"] == "STOLEN_FLAGGED"
    assert deal1["status"] == "REFUNDED_TO_BUYER"
    assert contract.is_serial_blacklisted("ROLEX", "STOLEN100") is True

    assert deal2["verdict"] == "AUTHENTIC_CLEAN"
    assert deal2["status"] == "SETTLED_TO_SELLER"
    assert contract.is_serial_blacklisted("PATEK", "CLEAN200") is False
