import pytest
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem


def test_cart_locking_behavior(client, db_session):
    # Create group via API
    resp = client.post("/api/v1/groups", json={
        "title": "Exam Prep Snacks",
        "delivery_location": "Hostel 4, Study Room",
        "cart_closing_minutes": 15,
        "participant_limit": 10,
        "fee_policy": "EQUAL_SPLIT"
    })
    assert resp.status_code == 200
    group_data = resp.json()
    group_id = group_data["id"]
    invite_code = group_data["invite_code"]

    # Join as guest participant
    join_resp = client.post(f"/api/v1/groups/{invite_code}/join", json={
        "display_name": "Devansh"
    })
    assert join_resp.status_code == 200
    p_data = join_resp.json()
    p_id = p_data["id"]

    # Add item to cart with participant session token
    add_resp = client.post(
        f"/api/v1/groups/{group_id}/cart/items?participant_id={p_id}",
        headers={"X-Session-Token": p_data["session_token"]},
        json={"product_id": "p-maggi", "quantity": 2}
    )
    assert add_resp.status_code == 200

    # Lock the cart with host session token
    lock_resp = client.post(
        f"/api/v1/groups/{group_id}/lock",
        headers={"X-Session-Token": group_data["host_session_token"]}
    )
    assert lock_resp.status_code == 200
    assert lock_resp.json()["cart_status"] == "LOCKED"

    # Attempting to add an item to locked cart MUST fail with 400
    fail_add = client.post(
        f"/api/v1/groups/{group_id}/cart/items?participant_id={p_id}",
        headers={"X-Session-Token": p_data["session_token"]},
        json={"product_id": "p-redbull", "quantity": 1}
    )
    assert fail_add.status_code == 400
    assert "Cannot add items" in fail_add.json()["detail"]


def test_group_summary_grouped_products(client, db_session):
    # Create group and add items from two participants
    resp = client.post("/api/v1/groups", json={
        "title": "Hostel Midnight Feast",
        "delivery_location": "Wing C",
        "fee_policy": "EQUAL_SPLIT"
    })
    group_data = resp.json()
    gid = group_data["id"]
    code = group_data["invite_code"]

    j1 = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "P1"}).json()
    j2 = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "P2"}).json()

    # Both order Maggi with their session tokens
    client.post(
        f"/api/v1/groups/{gid}/cart/items?participant_id={j1['id']}",
        headers={"X-Session-Token": j1["session_token"]},
        json={"product_id": "p-maggi", "quantity": 3}
    )
    client.post(
        f"/api/v1/groups/{gid}/cart/items?participant_id={j2['id']}",
        headers={"X-Session-Token": j2["session_token"]},
        json={"product_id": "p-maggi", "quantity": 2}
    )

    # Summary
    summary_resp = client.get(f"/api/v1/groups/{gid}/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()

    # Maggi total quantity must be 3 + 2 = 5!
    maggi_group = next(g for g in summary["grouped_products"] if g["product_id"] == "p-maggi")
    assert maggi_group["total_quantity"] == 5
    assert "P1" in maggi_group["ordered_by"]
    assert "P2" in maggi_group["ordered_by"]


def test_privileged_operations_host_authorization_security(client):
    """
    Task 2: Audit and enforce host authorization across all privileged operations:
    - Unauthenticated callers rejected (401)
    - Non-host participants rejected (403)
    - Hosts from different groups rejected (403)
    - Genuine host succeeds (200)
    Tested across:
    1. /groups/{id}/lock and /groups/{id}/reopen
    2. /groups/{id}/billing/policy
    3. /groups/{id}/merchant-order (POST) and /status (PATCH)
    """
    # 1. Setup Group A (Host A, Participant A)
    grp_a = client.post("/api/v1/groups", json={
        "title": "Group A Host Test",
        "delivery_location": "Hostel A",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid_a = grp_a["id"]
    code_a = grp_a["invite_code"]
    host_a_token = grp_a["host_session_token"]

    part_a = client.post(f"/api/v1/groups/{code_a}/join", json={"display_name": "Member A"}).json()
    member_a_token = part_a["session_token"]

    # 2. Setup Group B (Host B)
    grp_b = client.post("/api/v1/groups", json={
        "title": "Group B Host Test",
        "delivery_location": "Hostel B",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    host_b_token = grp_b["host_session_token"]

    # --- Test 1: Cart Locking & Reopening ---
    # 1a. Unauthenticated -> 401
    resp = client.post(f"/api/v1/groups/{gid_a}/lock")
    assert resp.status_code == 401

    # 1b. Member A (non-host in Group A) -> 403
    resp = client.post(f"/api/v1/groups/{gid_a}/lock", headers={"X-Session-Token": member_a_token})
    assert resp.status_code == 403

    # 1c. Host B (host from different group) -> 403
    resp = client.post(f"/api/v1/groups/{gid_a}/lock", headers={"X-Session-Token": host_b_token})
    assert resp.status_code == 403

    # 1d. Genuine Host A -> 200
    resp = client.post(f"/api/v1/groups/{gid_a}/lock", headers={"X-Session-Token": host_a_token})
    assert resp.status_code == 200
    assert resp.json()["cart_status"] == "LOCKED"

    # Reopen tests:
    # Non-host -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/reopen", headers={"X-Session-Token": member_a_token}).status_code == 403
    # Host B -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/reopen", headers={"X-Session-Token": host_b_token}).status_code == 403
    # Genuine Host A -> 200
    resp_reopen = client.post(f"/api/v1/groups/{gid_a}/reopen", headers={"X-Session-Token": host_a_token})
    assert resp_reopen.status_code == 200
    assert resp_reopen.json()["cart_status"] == "OPEN"

    # --- Test 2: Billing Policy Updates ---
    policy_payload = {"fee_policy": "HOST_COVERS"}
    # 2a. Unauthenticated -> 401
    assert client.post(f"/api/v1/groups/{gid_a}/billing/policy", json=policy_payload).status_code == 401
    # 2b. Member A (non-host) -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/billing/policy", headers={"X-Session-Token": member_a_token}, json=policy_payload).status_code == 403
    # 2c. Host B -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/billing/policy", headers={"X-Session-Token": host_b_token}, json=policy_payload).status_code == 403
    # 2d. Genuine Host A -> 200
    resp_policy = client.post(f"/api/v1/groups/{gid_a}/billing/policy", headers={"X-Session-Token": host_a_token}, json=policy_payload)
    assert resp_policy.status_code == 200
    assert resp_policy.json()["fee_policy"] == "HOST_COVERS"

    # --- Test 3: Merchant Orders ---
    order_payload = {"platform_name": "Blinkit", "external_order_id": "ORD-12345", "estimated_delivery_minutes": 20}
    # 3a. Unauthenticated -> 401
    assert client.post(f"/api/v1/groups/{gid_a}/merchant-order", json=order_payload).status_code == 401
    # 3b. Member A -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/merchant-order", headers={"X-Session-Token": member_a_token}, json=order_payload).status_code == 403
    # 3c. Host B -> 403
    assert client.post(f"/api/v1/groups/{gid_a}/merchant-order", headers={"X-Session-Token": host_b_token}, json=order_payload).status_code == 403
    # 3d. Genuine Host A -> 200
    resp_order = client.post(f"/api/v1/groups/{gid_a}/merchant-order", headers={"X-Session-Token": host_a_token}, json=order_payload)
    assert resp_order.status_code == 200
    assert resp_order.json()["status"] == "PLACED"

    # Status update:
    status_payload = {"status": "OUT_FOR_DELIVERY"}
    # Non-host -> 403
    assert client.patch(f"/api/v1/groups/{gid_a}/merchant-order/status", headers={"X-Session-Token": member_a_token}, json=status_payload).status_code == 403
    # Host B -> 403
    assert client.patch(f"/api/v1/groups/{gid_a}/merchant-order/status", headers={"X-Session-Token": host_b_token}, json=status_payload).status_code == 403
    # Genuine Host A -> 200
    resp_status = client.patch(f"/api/v1/groups/{gid_a}/merchant-order/status", headers={"X-Session-Token": host_a_token}, json=status_payload)
    assert resp_status.status_code == 200
    assert resp_status.json()["status"] == "OUT_FOR_DELIVERY"


def test_cart_item_participant_ownership_security(client):
    """
    Task 2: A participant cannot impersonate another participant or tamper with their cart items:
    - Adding items with someone else's ID is rejected.
    - Updating someone else's item is rejected (unless host).
    - Deleting someone else's item is rejected (unless host).
    """
    grp = client.post("/api/v1/groups", json={
        "title": "Cart Security Test",
        "delivery_location": "Hostel C",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid = grp["id"]
    code = grp["invite_code"]
    host_token = grp["host_session_token"]

    p_alice = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "Alice"}).json()
    p_bob = client.post(f"/api/v1/groups/{code}/join", json={"display_name": "Bob"}).json()

    # 1. Impersonation on add item:
    # Bob sends Bob's session token, but specifies Alice's participant_id
    resp_impersonate = client.post(
        f"/api/v1/groups/{gid}/cart/items?participant_id={p_alice['id']}",
        headers={"X-Session-Token": p_bob["session_token"]},
        json={"product_id": "p-maggi", "quantity": 1}
    )
    assert resp_impersonate.status_code == 403
    assert "does not match" in resp_impersonate.json()["detail"].lower()

    # Alice legitimately adds item
    add_resp = client.post(
        f"/api/v1/groups/{gid}/cart/items?participant_id={p_alice['id']}",
        headers={"X-Session-Token": p_alice["session_token"]},
        json={"product_id": "p-maggi", "quantity": 1}
    )
    assert add_resp.status_code == 200
    item_id = add_resp.json()["id"]

    # 2. Bob attempts to modify Alice's cart item -> 403
    resp_mod = client.patch(
        f"/api/v1/groups/{gid}/cart/items/{item_id}",
        headers={"X-Session-Token": p_bob["session_token"]},
        json={"quantity": 10}
    )
    assert resp_mod.status_code == 403
    assert "only modify your own" in resp_mod.json()["detail"].lower()

    # 3. Bob attempts to delete Alice's cart item -> 403
    resp_del = client.delete(
        f"/api/v1/groups/{gid}/cart/items/{item_id}",
        headers={"X-Session-Token": p_bob["session_token"]}
    )
    assert resp_del.status_code == 403
    assert "only remove your own" in resp_del.json()["detail"].lower()

    # 4. Alice can modify her own item -> 200
    resp_alice_mod = client.patch(
        f"/api/v1/groups/{gid}/cart/items/{item_id}",
        headers={"X-Session-Token": p_alice["session_token"]},
        json={"quantity": 2}
    )
    assert resp_alice_mod.status_code == 200
    assert resp_alice_mod.json()["quantity"] == 2

    # 5. Host can remove an item as group administrator -> 200
    resp_host_del = client.delete(
        f"/api/v1/groups/{gid}/cart/items/{item_id}",
        headers={"X-Session-Token": host_token}
    )
    assert resp_host_del.status_code == 200


def test_cart_ownership_and_participant_authorization_matrix(client):
    """
    Task 3: Focused audit of cart ownership and participant authorization.
    Verifies:
    1. Unauthenticated callers are rejected on POST, PATCH, and DELETE (401).
    2. Participant cannot impersonate another participant (403).
    3. Caller identity derived automatically when participant_id omitted.
    4. Participant cannot modify or delete another participant's items (403).
    5. Cross-group item isolation (accessing Group B item via Group A endpoint) -> 400.
    6. Host from Group B cannot modify/delete items or add items to Group A (403).
    7. Locked group prevents cart mutations for all participants and host (400).
    8. Product prices and totals calculated on server, not client-supplied.
    9. Quantity validation and capping (invalid quantity -> 422, capping > 50 -> 400).
    10. Legitimate participant can update notes, change quantity, and remove item (200).
    11. Legitimate host can update or remove participant items in their own group (200).
    """
    # 1. Setup Group A
    grp_a = client.post("/api/v1/groups", json={
        "title": "Group A Cart Matrix",
        "delivery_location": "Hostel 1",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid_a = grp_a["id"]
    code_a = grp_a["invite_code"]
    host_a_token = grp_a["host_session_token"]

    p_alice = client.post(f"/api/v1/groups/{code_a}/join", json={"display_name": "Alice"}).json()
    p_bob = client.post(f"/api/v1/groups/{code_a}/join", json={"display_name": "Bob"}).json()
    alice_token = p_alice["session_token"]
    bob_token = p_bob["session_token"]

    # 2. Setup Group B
    grp_b = client.post("/api/v1/groups", json={
        "title": "Group B Cart Matrix",
        "delivery_location": "Hostel 2",
        "fee_policy": "EQUAL_SPLIT"
    }).json()
    gid_b = grp_b["id"]
    code_b = grp_b["invite_code"]
    host_b_token = grp_b["host_session_token"]

    p_charlie = client.post(f"/api/v1/groups/{code_b}/join", json={"display_name": "Charlie"}).json()
    charlie_token = p_charlie["session_token"]

    # --- REQUIREMENT 1: Unauthenticated callers rejected ---
    # POST /items without credentials -> 401
    unauth_post = client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        json={"product_id": "p-maggi", "quantity": 1}
    )
    assert unauth_post.status_code == 401

    # Add item legitimately for Alice in Group A
    alice_add = client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": alice_token},
        json={"product_id": "p-maggi", "quantity": 2, "item_notes": "Extra spicy"}
    )
    assert alice_add.status_code == 200
    item_a_id = alice_add.json()["id"]
    # Check server-calculated prices: Maggi unit price is 1400 paise (Rs 14.0), total for 2 is 2800 paise
    assert alice_add.json()["unit_price_paise"] == 1400
    assert alice_add.json()["item_subtotal_paise"] == 2800

    # PATCH /items/{id} without credentials -> 401
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        json={"quantity": 3}
    ).status_code == 401

    # DELETE /items/{id} without credentials -> 401
    assert client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}"
    ).status_code == 401

    # --- REQUIREMENT 2 & 5: Participant impersonation rejected ---
    # Bob attempts to add item using Alice's participant_id
    impersonate_post = client.post(
        f"/api/v1/groups/{gid_a}/cart/items?participant_id={p_alice['id']}",
        headers={"X-Session-Token": bob_token},
        json={"product_id": "p-redbull", "quantity": 1}
    )
    assert impersonate_post.status_code == 403

    # Identity automatically derived when participant_id omitted
    auto_post = client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": bob_token},
        json={"product_id": "p-redbull", "quantity": 1}
    )
    assert auto_post.status_code == 200
    assert auto_post.json()["participant_id"] == p_bob["id"]
    item_bob_id = auto_post.json()["id"]

    # --- REQUIREMENT 4: Participant tampering with another participant's item rejected ---
    # Bob tries to modify Alice's item -> 403
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": bob_token},
        json={"quantity": 5}
    ).status_code == 403

    # Bob tries to delete Alice's item -> 403
    assert client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": bob_token}
    ).status_code == 403

    # --- REQUIREMENT 3 & 5: Cross-group item isolation ---
    # Add item for Charlie in Group B
    charlie_add = client.post(
        f"/api/v1/groups/{gid_b}/cart/items",
        headers={"X-Session-Token": charlie_token},
        json={"product_id": "p-lays", "quantity": 1}
    )
    assert charlie_add.status_code == 200
    item_b_id = charlie_add.json()["id"]

    # Alice tries to modify Charlie's item from Group B via Group A endpoint -> 400
    cross_mod = client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_b_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": 2}
    )
    assert cross_mod.status_code == 400
    assert "not belong to the specified group" in cross_mod.json()["detail"].lower()

    # Host A tries to delete Charlie's item from Group B via Group A endpoint -> 400
    cross_del = client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_b_id}",
        headers={"X-Session-Token": host_a_token}
    )
    assert cross_del.status_code == 400
    assert "not belong to the specified group" in cross_del.json()["detail"].lower()

    # --- REQUIREMENT 4 & 5: Unauthorized host actions across groups ---
    # Host B tries to modify Alice's item in Group A -> 403
    host_b_mod = client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": host_b_token},
        json={"quantity": 10}
    )
    assert host_b_mod.status_code == 403

    # Host B tries to delete Alice's item in Group A -> 403
    host_b_del = client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": host_b_token}
    )
    assert host_b_del.status_code == 403

    # Host B tries to add items into Group A -> 403
    host_b_add = client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": host_b_token},
        json={"product_id": "p-maggi", "quantity": 1}
    )
    assert host_b_add.status_code == 403

    # --- REQUIREMENT 5 & 6: Quantity validation and capping ---
    # Invalid quantity on add (0) -> 422
    assert client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": alice_token},
        json={"product_id": "p-coke", "quantity": 0}
    ).status_code == 422

    # Invalid negative quantity on update -> 422
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": -2}
    ).status_code == 422

    # Capping total quantity to 50 when adding to existing product in cart:
    # Alice already has 2 Maggi. Adding 49 more -> total 51 > 50 -> 400
    cap_resp = client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": alice_token},
        json={"product_id": "p-maggi", "quantity": 49}
    )
    assert cap_resp.status_code == 400
    assert "cannot exceed 50" in cap_resp.json()["detail"].lower()

    # --- REQUIREMENT 7: Locked group prevents mutations for everyone ---
    # Host A locks Group A
    lock_resp = client.post(
        f"/api/v1/groups/{gid_a}/lock",
        headers={"X-Session-Token": host_a_token}
    )
    assert lock_resp.status_code == 200

    # Participant Alice cannot add item when locked -> 400
    assert client.post(
        f"/api/v1/groups/{gid_a}/cart/items",
        headers={"X-Session-Token": alice_token},
        json={"product_id": "p-coke", "quantity": 1}
    ).status_code == 400

    # Participant Alice cannot update item when locked -> 400
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": 3}
    ).status_code == 400

    # Host A cannot update item while cart is locked -> 400
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": host_a_token},
        json={"quantity": 3}
    ).status_code == 400

    # Host A cannot delete item while cart is locked -> 400
    assert client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": host_a_token}
    ).status_code == 400

    # Host A reopens Group A
    client.post(
        f"/api/v1/groups/{gid_a}/reopen",
        headers={"X-Session-Token": host_a_token}
    )

    # --- REQUIREMENT 4 & 8: Legitimate participant and host operations ---
    # Alice updates her own item notes and quantity -> 200
    alice_update = client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": 4, "item_notes": "Mild spicy"}
    )
    assert alice_update.status_code == 200
    assert alice_update.json()["quantity"] == 4
    assert alice_update.json()["item_notes"] == "Mild spicy"

    # Host A can intervene and adjust quantity for an item in Group A -> 200
    host_update = client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": host_a_token},
        json={"quantity": 3}
    )
    assert host_update.status_code == 200
    assert host_update.json()["quantity"] == 3

    # Host A can remove Bob's item -> 200
    host_del_bob = client.delete(
        f"/api/v1/groups/{gid_a}/cart/items/{item_bob_id}",
        headers={"X-Session-Token": host_a_token}
    )
    assert host_del_bob.status_code == 200

    # Alice sets quantity to 0 -> 200 (removes item)
    alice_zero = client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": 0}
    )
    assert alice_zero.status_code == 200

    # Item is now gone -> 404
    assert client.patch(
        f"/api/v1/groups/{gid_a}/cart/items/{item_a_id}",
        headers={"X-Session-Token": alice_token},
        json={"quantity": 1}
    ).status_code == 404

