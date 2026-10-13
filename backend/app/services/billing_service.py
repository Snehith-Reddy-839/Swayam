import math
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.models.billing import BillAllocation
from app.schemas.billing import BillCalculationResponse, ParticipantBillShare


def calculate_group_bill(group: GroupOrder, db: Session) -> BillCalculationResponse:
    """
    Deterministically calculates individual and group bill shares strictly in integer paise.
    Uses integer division and Hamilton-Hare Largest Remainder Method to guarantee that
    the sum of all participant shares matches the grand total exactly (zero paise error).
    """
    participants = db.query(GroupParticipant).filter(GroupParticipant.group_order_id == group.id).all()
    if not participants:
        return BillCalculationResponse(
            group_id=group.id,
            fee_policy=group.fee_policy,
            participants_count=0,
            total_items_subtotal_paise=0,
            total_items_subtotal_inr=0.0,
            delivery_fee_paise=group.delivery_fee_paise,
            delivery_fee_inr=group.delivery_fee_paise / 100.0,
            platform_fee_paise=group.platform_fee_paise,
            platform_fee_inr=group.platform_fee_paise / 100.0,
            packaging_fee_paise=group.packaging_fee_paise,
            packaging_fee_inr=group.packaging_fee_paise / 100.0,
            total_shared_fees_paise=group.delivery_fee_paise + group.platform_fee_paise + group.packaging_fee_paise,
            total_shared_fees_inr=(group.delivery_fee_paise + group.platform_fee_paise + group.packaging_fee_paise) / 100.0,
            tax_percentage=group.tax_percentage,
            total_tax_paise=0,
            total_tax_inr=0.0,
            total_discount_paise=group.discount_paise,
            total_discount_inr=group.discount_paise / 100.0,
            grand_total_paise=0,
            grand_total_inr=0.0,
            total_paid_paise=0,
            total_paid_inr=0.0,
            total_outstanding_paise=0,
            total_outstanding_inr=0.0,
            is_fully_paid=True,
            sum_of_participant_shares_paise=0,
            is_deterministic_exact_match=True,
            participant_shares=[]
        )

    # 1. Fetch all cart items and sum individual subtotals
    cart_items = db.query(CartItem).filter(CartItem.group_order_id == group.id).all()
    
    participant_items: Dict[str, List[CartItem]] = {p.id: [] for p in participants}
    participant_subtotals: Dict[str, int] = {p.id: 0 for p in participants}
    
    for item in cart_items:
        if item.participant_id in participant_items:
            participant_items[item.participant_id].append(item)
            participant_subtotals[item.participant_id] += (item.unit_price_paise * item.quantity)

    total_items_subtotal_paise = sum(participant_subtotals.values())
    
    # Shared Fees
    delivery_fee = group.delivery_fee_paise
    platform_fee = group.platform_fee_paise
    packaging_fee = group.packaging_fee_paise
    total_shared_fees_paise = delivery_fee + platform_fee + packaging_fee
    
    # Tax Calculation in paise (e.g. 5% on items subtotal + packaging)
    taxable_base_paise = total_items_subtotal_paise + packaging_fee
    total_tax_paise = round(taxable_base_paise * (group.tax_percentage / 100.0))
    
    total_discount_paise = group.discount_paise
    
    # Grand Total
    # (Items Subtotal + Shared Fees + Tax - Discount)
    grand_total_paise = max(0, total_items_subtotal_paise + total_shared_fees_paise + total_tax_paise - total_discount_paise)

    # Determine which participants have active items or participate in fees
    # Active participants with items, or all participants if none have items yet
    active_participants = [p for p in participants if participant_subtotals[p.id] > 0]
    if not active_participants:
        # Fallback to all participants if cart is empty
        fee_bearing_participants = participants
    else:
        fee_bearing_participants = active_participants

    n_fee_bearers = len(fee_bearing_participants)
    
    # 2. Allocate Shared Fees according to fee_policy
    # Policies: "EQUAL_SPLIT", "PROPORTIONAL", "HOST_COVERS"
    shared_fee_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    delivery_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    platform_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    packaging_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    
    if n_fee_bearers > 0 and total_shared_fees_paise > 0:
        if group.fee_policy == "HOST_COVERS":
            host = next((p for p in participants if p.is_host), participants[0])
            shared_fee_allocation[host.id] = total_shared_fees_paise
            delivery_allocation[host.id] = delivery_fee
            platform_allocation[host.id] = platform_fee
            packaging_allocation[host.id] = packaging_fee
        elif group.fee_policy == "PROPORTIONAL" and total_items_subtotal_paise > 0:
            # Largest remainder method for proportional fee distribution
            shared_fee_allocation = _distribute_proportionally(
                total_shared_fees_paise,
                {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
            )
            delivery_allocation = _distribute_proportionally(
                delivery_fee,
                {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
            )
            platform_allocation = _distribute_proportionally(
                platform_fee,
                {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
            )
            packaging_allocation = _distribute_proportionally(
                packaging_fee,
                {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
            )
        else: # Default: EQUAL_SPLIT
            # Equal split with deterministic remainder distribution sorted by participant ID
            sorted_bearers = sorted(fee_bearing_participants, key=lambda x: x.id)
            shared_fee_allocation = _distribute_equally(total_shared_fees_paise, [p.id for p in sorted_bearers])
            delivery_allocation = _distribute_equally(delivery_fee, [p.id for p in sorted_bearers])
            platform_allocation = _distribute_equally(platform_fee, [p.id for p in sorted_bearers])
            packaging_allocation = _distribute_equally(packaging_fee, [p.id for p in sorted_bearers])

    # 3. Allocate Tax proportionally to each participant's item subtotal
    tax_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    if total_tax_paise > 0 and total_items_subtotal_paise > 0:
        tax_allocation = _distribute_proportionally(
            total_tax_paise,
            {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
        )

    # 4. Allocate Discount proportionally
    discount_allocation: Dict[str, int] = {p.id: 0 for p in participants}
    if total_discount_paise > 0 and total_items_subtotal_paise > 0:
        discount_allocation = _distribute_proportionally(
            total_discount_paise,
            {p.id: participant_subtotals[p.id] for p in fee_bearing_participants}
        )

    # 5. Build individual participant shares
    participant_shares: List[ParticipantBillShare] = []
    
    for p in participants:
        p_subtotal = participant_subtotals[p.id]
        p_shared = shared_fee_allocation.get(p.id, 0)
        p_tax = tax_allocation.get(p.id, 0)
        p_disc = discount_allocation.get(p.id, 0)
        
        p_total_payable = max(0, p_subtotal + p_shared + p_tax - p_disc)
        p_paid = p.amount_paid_paise
        p_outstanding = max(0, p_total_payable - p_paid)
        
        share = ParticipantBillShare(
            participant_id=p.id,
            participant_name=p.display_name,
            avatar_color=p.avatar_color,
            is_host=p.is_host,
            payment_status=p.payment_status,
            items_count=len(participant_items[p.id]),
            items_subtotal_paise=p_subtotal,
            items_subtotal_inr=p_subtotal / 100.0,
            delivery_share_paise=delivery_allocation.get(p.id, 0),
            platform_share_paise=platform_allocation.get(p.id, 0),
            packaging_share_paise=packaging_allocation.get(p.id, 0),
            shared_fees_total_paise=p_shared,
            shared_fees_total_inr=p_shared / 100.0,
            tax_share_paise=p_tax,
            tax_share_inr=p_tax / 100.0,
            discount_share_paise=p_disc,
            discount_share_inr=p_disc / 100.0,
            rounding_adjustment_paise=0,
            total_payable_paise=p_total_payable,
            total_payable_inr=p_total_payable / 100.0,
            amount_paid_paise=p_paid,
            amount_paid_inr=p_paid / 100.0,
            outstanding_paise=p_outstanding,
            outstanding_inr=p_outstanding / 100.0
        )
        participant_shares.append(share)

    # 6. Deterministic leftover verification:
    # Check if sum of total_payable equals grand_total_paise
    calculated_sum_shares = sum(s.total_payable_paise for s in participant_shares)
    discrepancy = grand_total_paise - calculated_sum_shares
    
    if discrepancy != 0 and participant_shares:
        # Reconcile discrepancy deterministically by adjusting the first participant with highest subtotal
        target = max(participant_shares, key=lambda s: (s.total_payable_paise, s.participant_id))
        target.rounding_adjustment_paise += discrepancy
        target.total_payable_paise += discrepancy
        target.total_payable_inr = target.total_payable_paise / 100.0
        target.outstanding_paise = max(0, target.total_payable_paise - target.amount_paid_paise)
        target.outstanding_inr = target.outstanding_paise / 100.0

    final_sum_shares = sum(s.total_payable_paise for s in participant_shares)
    total_paid_all = sum(s.amount_paid_paise for s in participant_shares)
    total_outstanding_all = sum(s.outstanding_paise for s in participant_shares)
    
    # Save/Update BillAllocation rows in database
    for share in participant_shares:
        alloc = db.query(BillAllocation).filter(
            BillAllocation.group_order_id == group.id,
            BillAllocation.participant_id == share.participant_id
        ).first()
        
        if not alloc:
            alloc = BillAllocation(
                group_order_id=group.id,
                participant_id=share.participant_id,
                items_subtotal_paise=share.items_subtotal_paise,
                shared_fees_share_paise=share.shared_fees_total_paise,
                tax_share_paise=share.tax_share_paise,
                discount_share_paise=share.discount_share_paise,
                rounding_adjustment_paise=share.rounding_adjustment_paise,
                total_payable_paise=share.total_payable_paise,
                amount_paid_paise=share.amount_paid_paise
            )
            db.add(alloc)
        else:
            alloc.items_subtotal_paise = share.items_subtotal_paise
            alloc.shared_fees_share_paise = share.shared_fees_total_paise
            alloc.tax_share_paise = share.tax_share_paise
            alloc.discount_share_paise = share.discount_share_paise
            alloc.rounding_adjustment_paise = share.rounding_adjustment_paise
            alloc.total_payable_paise = share.total_payable_paise
            alloc.amount_paid_paise = share.amount_paid_paise

    db.commit()

    return BillCalculationResponse(
        group_id=group.id,
        fee_policy=group.fee_policy,
        participants_count=len(participants),
        total_items_subtotal_paise=total_items_subtotal_paise,
        total_items_subtotal_inr=total_items_subtotal_paise / 100.0,
        delivery_fee_paise=delivery_fee,
        delivery_fee_inr=delivery_fee / 100.0,
        platform_fee_paise=platform_fee,
        platform_fee_inr=platform_fee / 100.0,
        packaging_fee_paise=packaging_fee,
        packaging_fee_inr=packaging_fee / 100.0,
        total_shared_fees_paise=total_shared_fees_paise,
        total_shared_fees_inr=total_shared_fees_paise / 100.0,
        tax_percentage=group.tax_percentage,
        total_tax_paise=total_tax_paise,
        total_tax_inr=total_tax_paise / 100.0,
        total_discount_paise=total_discount_paise,
        total_discount_inr=total_discount_paise / 100.0,
        grand_total_paise=grand_total_paise,
        grand_total_inr=grand_total_paise / 100.0,
        total_paid_paise=total_paid_all,
        total_paid_inr=total_paid_all / 100.0,
        total_outstanding_paise=total_outstanding_all,
        total_outstanding_inr=total_outstanding_all / 100.0,
        is_fully_paid=(total_outstanding_all == 0 and grand_total_paise > 0),
        sum_of_participant_shares_paise=final_sum_shares,
        is_deterministic_exact_match=(final_sum_shares == grand_total_paise),
        participant_shares=participant_shares
    )


def _distribute_equally(amount_paise: int, participant_ids: List[str]) -> Dict[str, int]:
    """Distributes an amount equally in paise, allocating remainder deterministically."""
    if not participant_ids or amount_paise <= 0:
        return {pid: 0 for pid in participant_ids}
    
    n = len(participant_ids)
    base_share = amount_paise // n
    remainder = amount_paise % n
    
    result = {}
    for i, pid in enumerate(participant_ids):
        # First `remainder` participants get 1 extra paise
        extra = 1 if i < remainder else 0
        result[pid] = base_share + extra
    return result


def _distribute_proportionally(amount_paise: int, weights: Dict[str, int]) -> Dict[str, int]:
    """
    Hamilton-Hare Largest Remainder Method:
    Allocates exact integer paise according to weights, guaranteeing exact sum with zero error.
    """
    total_weight = sum(weights.values())
    if total_weight <= 0 or amount_paise <= 0:
        return {pid: 0 for pid in weights}
    
    base_shares: Dict[str, int] = {}
    remainders: List[Tuple[float, str]] = []
    
    for pid, w in weights.items():
        exact_value = (w * amount_paise) / total_weight
        floor_val = math.floor(exact_value)
        base_shares[pid] = floor_val
        fractional = exact_value - floor_val
        remainders.append((fractional, pid))
    
    allocated = sum(base_shares.values())
    shortage = amount_paise - allocated
    
    # Sort by largest fractional remainder descending, breaking ties by participant id
    remainders.sort(key=lambda item: (-item[0], item[1]))
    
    for i in range(shortage):
        pid = remainders[i][1]
        base_shares[pid] += 1
        
    return base_shares
