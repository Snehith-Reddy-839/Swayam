import pytest
from app.models.group import GroupOrder, GroupParticipant


def test_auth_and_guest_session_flow(client):
    # 1. Guest session creation
    resp = client.post("/api/v1/auth/guest-session", json={
        "display_name": "LateNightCraver",
        "avatar_color": "#FF5C00"
    })
    assert resp.status_code == 200
    guest_data = resp.json()
    assert guest_data["display_name"] == "LateNightCraver"
    assert "session_token" in guest_data

    # 2. User registration
    reg_resp = client.post("/api/v1/auth/register", json={
        "name": "Host Aditya",
        "email": "aditya@hostel.edu",
        "phone": "+919988776655",
        "password": "securepassword123"
    })
    assert reg_resp.status_code == 200
    token_data = reg_resp.json()
    assert "access_token" in token_data

    # 3. User login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "aditya@hostel.edu",
        "password": "securepassword123"
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_products_catalog_api(client):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    data = resp.json()
    assert "products" in data
    assert "categories" in data
    assert len(data["products"]) >= 3


def test_manual_upi_confirmation_by_host(client, db_session):
    # Create group
    grp = client.post("/api/v1/groups", json={
        "title": "Pizza & Soda Night",
        "delivery_location": "Common Room",
        "fee_policy": "EQUAL_SPLIT"
    }).json()

    # Host is first participant
    parts = client.get(f"/api/v1/groups/{grp['id']}/participants").json()
    host_p = parts[0]

    # Join a friend
    friend_p = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={
        "display_name": "Siddharth"
    }).json()

    # Friend adds an item
    client.post(f"/api/v1/groups/{grp['id']}/cart/items?participant_id={friend_p['id']}", json={
        "product_id": "p-maggi",
        "quantity": 2
    })

    # Host manually marks payment received using host's session_token
    confirm_resp = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": friend_p["id"],
        "host_participant_id": host_p["id"],
        "session_token": grp.get("host_session_token"),
        "upi_reference": "UTR_TEST_123456",
        "notes": "Verified in host Google Pay app"
    })
    assert confirm_resp.status_code == 200
    confirm_data = confirm_resp.json()
    assert confirm_data["status"] == "PAID"
    assert confirm_data["payment_mode"] == "UPI_MANUAL"
    assert confirm_data["receipt_id"] is not None

    # Fetch receipt
    rcpt = client.get(f"/api/v1/receipts/{confirm_data['receipt_token']}").json()
    assert rcpt["participant_name"] == "Siddharth"
    assert rcpt["total_paid_paise"] > 0


def test_unauthorized_non_host_payment_confirmation(client):
    # Create group
    grp = client.post("/api/v1/groups", json={
        "title": "Unauthorized Test Group",
        "delivery_location": "Room 101",
        "fee_policy": "EQUAL_SPLIT"
    }).json()

    # Join two friends
    p1 = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Friend 1"}).json()
    p2 = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Friend 2"}).json()

    # Add item
    client.post(f"/api/v1/groups/{grp['id']}/cart/items?participant_id={p1['id']}", json={
        "product_id": "p-maggi",
        "quantity": 1
    })

    # Friend 2 (non-host) tries to confirm Friend 1's payment
    resp = client.post("/api/v1/payments/host-manual-confirm", json={
        "participant_id": p1["id"],
        "host_participant_id": p2["id"],
        "upi_reference": "UTR_FAKE",
        "notes": "Unauthorized confirmation attempt"
    })
    assert resp.status_code == 400
    assert "Only the group host can perform manual payment confirmation" in resp.json()["detail"]


def test_demo_payment_failure_scenario(client):
    grp = client.post("/api/v1/groups", json={
        "title": "Failure Demo Group",
        "delivery_location": "Hostel Mess",
        "fee_policy": "EQUAL_SPLIT"
    }).json()

    p = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Rahul"}).json()
    client.post(
        f"/api/v1/groups/{grp['id']}/cart/items?participant_id={p['id']}",
        headers={"X-Session-Token": p["session_token"]},
        json={"product_id": "p-kurkure", "quantity": 2}
    )

    # Initiate payment attempt
    init_resp = client.post(
        "/api/v1/payments/initiate",
        headers={"X-Session-Token": p["session_token"]},
        json={
            "participant_id": p["id"],
            "session_token": p["session_token"],
            "payment_mode": "DEMO"
        }
    ).json()
    attempt_id = init_resp["attempt_id"]

    # Verify with FAILURE demo outcome using participant's session_token
    fail_resp = client.post("/api/v1/payments/verify", json={
        "payment_attempt_id": attempt_id,
        "payment_mode": "DEMO",
        "participant_id": p["id"],
        "session_token": p.get("session_token"),
        "demo_outcome": "FAILURE"
    }).json()

    assert fail_resp["status"] == "FAILED"
    assert fail_resp["receipt_id"] is None
    assert fail_resp["failure_reason"] is not None


def test_combined_group_summary_receipt_api(client):
    grp = client.post("/api/v1/groups", json={
        "title": "Group Summary Test",
        "delivery_location": "Hostel Terrace",
        "fee_policy": "EQUAL_SPLIT"
    }).json()

    p = client.post(f"/api/v1/groups/{grp['invite_code']}/join", json={"display_name": "Arjun"}).json()
    client.post(
        f"/api/v1/groups/{grp['id']}/cart/items?participant_id={p['id']}",
        headers={"X-Session-Token": p["session_token"]},
        json={"product_id": "p-redbull", "quantity": 3}
    )

    # Test summary by group UUID
    sum_by_id = client.get(f"/api/v1/receipts/groups/{grp['id']}/summary").json()
    assert sum_by_id["group_title"] == "Group Summary Test"
    assert sum_by_id["total_items_count"] == 3
    assert len(sum_by_id["grouped_products"]) == 1
    assert sum_by_id["grouped_products"][0]["total_quantity"] == 3

    # Test summary by 6-char invite code via receipts and groups routers
    sum_by_code = client.get(f"/api/v1/receipts/groups/{grp['invite_code']}/summary").json()
    assert sum_by_code["group_title"] == "Group Summary Test"
    assert sum_by_code["invite_code"] == grp["invite_code"]

    # Test via /groups/{code}/summary with both uppercase and lowercase code
    sum_via_groups = client.get(f"/api/v1/groups/{grp['invite_code']}/summary").json()
    assert sum_via_groups["group_title"] == "Group Summary Test"

    sum_via_lower = client.get(f"/api/v1/groups/{grp['invite_code'].lower()}/summary").json()
    assert sum_via_lower["group_title"] == "Group Summary Test"
