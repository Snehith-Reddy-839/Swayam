import pytest
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.services.billing_service import calculate_group_bill


def test_equal_split_deterministic_rounding(db_session):
    """
    Test that equal fee splitting distributes odd paise deterministically
    and that sum of individual shares exactly equals grand total.
    """
    # Create group with 3 participants
    group = GroupOrder(
        invite_code="TEST01",
        title="Hostel Night Maggi",
        host_name="Aman",
        delivery_location="Block A, Room 101",
        fee_policy="EQUAL_SPLIT",
        delivery_fee_paise=4000, # ₹40.00
        platform_fee_paise=1000, # ₹10.00
        packaging_fee_paise=1500, # ₹15.00
        tax_percentage=5.0,
        discount_paise=0
    )
    db_session.add(group)
    db_session.flush()

    p1 = GroupParticipant(group_order_id=group.id, display_name="Aman", is_host=True)
    p2 = GroupParticipant(group_order_id=group.id, display_name="Rohan", is_host=False)
    p3 = GroupParticipant(group_order_id=group.id, display_name="Sneha", is_host=False)
    db_session.add_all([p1, p2, p3])
    db_session.flush()

    # Aman orders 2 Maggi (2 * 1400 = 2800)
    # Rohan orders 1 Red Bull (1 * 12500 = 12500)
    # Sneha orders 3 Maggi (3 * 1400 = 4200)
    item1 = CartItem(group_order_id=group.id, participant_id=p1.id, product_id="p-maggi", quantity=2, unit_price_paise=1400)
    item2 = CartItem(group_order_id=group.id, participant_id=p2.id, product_id="p-redbull", quantity=1, unit_price_paise=12500)
    item3 = CartItem(group_order_id=group.id, participant_id=p3.id, product_id="p-maggi", quantity=3, unit_price_paise=1400)
    db_session.add_all([item1, item2, item3])
    db_session.commit()

    bill = calculate_group_bill(group, db_session)

    # Total items subtotal: 2800 + 12500 + 4200 = 19500 paise (₹195.00)
    assert bill.total_items_subtotal_paise == 19500

    # Total shared fees: 4000 + 1000 + 1500 = 6500 paise (₹65.00)
    assert bill.total_shared_fees_paise == 6500

    # Sum of participant shares must MATCH grand total down to the exact single paise
    sum_shares = sum(s.total_payable_paise for s in bill.participant_shares)
    assert sum_shares == bill.grand_total_paise
    assert bill.is_deterministic_exact_match is True


def test_proportional_split_policy(db_session):
    """
    Test proportional fee splitting where shared fees are divided by item subtotal.
    """
    group = GroupOrder(
        invite_code="TEST02",
        title="Late Study Group",
        host_name="Pooja",
        delivery_location="Girls Hostel 2",
        fee_policy="PROPORTIONAL",
        delivery_fee_paise=5000,
        platform_fee_paise=1000,
        packaging_fee_paise=1000,
        tax_percentage=0.0,
        discount_paise=1000 # ₹10 discount
    )
    db_session.add(group)
    db_session.flush()

    p1 = GroupParticipant(group_order_id=group.id, display_name="Pooja", is_host=True)
    p2 = GroupParticipant(group_order_id=group.id, display_name="Neha", is_host=False)
    db_session.add_all([p1, p2])
    db_session.flush()

    # Pooja orders ₹100, Neha orders ₹300
    it1 = CartItem(group_order_id=group.id, participant_id=p1.id, product_id="p-maggi", quantity=5, unit_price_paise=2000) # 10000 paise
    it2 = CartItem(group_order_id=group.id, participant_id=p2.id, product_id="p-lays", quantity=15, unit_price_paise=2000) # 30000 paise
    db_session.add_all([it1, it2])
    db_session.commit()

    bill = calculate_group_bill(group, db_session)

    # Subtotals: Pooja 10000, Neha 30000 -> Total 40000 (1:3 ratio)
    assert bill.total_items_subtotal_paise == 40000

    # Proportional check: Neha pays ~3x the shared fees of Pooja
    pooja_share = next(s for s in bill.participant_shares if s.participant_id == p1.id)
    neha_share = next(s for s in bill.participant_shares if s.participant_id == p2.id)

    assert neha_share.shared_fees_total_paise >= pooja_share.shared_fees_total_paise * 2.5
    # Strict paise equality
    assert (pooja_share.total_payable_paise + neha_share.total_payable_paise) == bill.grand_total_paise


def test_host_covers_shared_fees(db_session):
    """
    Test policy where host pays all delivery/platform/packaging fees.
    """
    group = GroupOrder(
        invite_code="TEST03",
        title="Host Generous Group",
        host_name="Karan",
        delivery_location="Flat 402",
        fee_policy="HOST_COVERS",
        delivery_fee_paise=4000,
        platform_fee_paise=1000,
        packaging_fee_paise=1000,
        tax_percentage=0.0
    )
    db_session.add(group)
    db_session.flush()

    host = GroupParticipant(group_order_id=group.id, display_name="Karan", is_host=True)
    guest = GroupParticipant(group_order_id=group.id, display_name="Vikas", is_host=False)
    db_session.add_all([host, guest])
    db_session.flush()

    # Each orders 1 item of 2000 paise
    i1 = CartItem(group_order_id=group.id, participant_id=host.id, product_id="p-lays", quantity=1, unit_price_paise=2000)
    i2 = CartItem(group_order_id=group.id, participant_id=guest.id, product_id="p-lays", quantity=1, unit_price_paise=2000)
    db_session.add_all([i1, i2])
    db_session.commit()

    bill = calculate_group_bill(group, db_session)
    guest_share = next(s for s in bill.participant_shares if s.participant_id == guest.id)
    host_share = next(s for s in bill.participant_shares if s.participant_id == host.id)

    # Guest should only pay for items: 2000 paise
    assert guest_share.shared_fees_total_paise == 0
    assert guest_share.total_payable_paise == 2000

    # Host should pay items (2000) + all shared fees (6000) = 8000 paise
    assert host_share.shared_fees_total_paise == 6000
    assert host_share.total_payable_paise == 8000
    assert (host_share.total_payable_paise + guest_share.total_payable_paise) == bill.grand_total_paise
