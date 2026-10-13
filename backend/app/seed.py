import uuid
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.product import ProductCategory, Product
from app.models.user import User, GuestSession
from app.models.group import GroupOrder, GroupParticipant
from app.models.cart import CartItem
from app.models.audit import AuditLog
from app.services.billing_service import calculate_group_bill
from app.services.auth_service import get_password_hash


def seed_demo_groups(db: Session):
    """Seeds the featured demo groups MUNCH9 and EXAM26 with participants and items."""
    # 1. Seed MUNCH9
    munch9 = db.query(GroupOrder).filter(GroupOrder.invite_code == "MUNCH9").first()
    if not munch9:
        print("Seeding demo group MUNCH9 (Hostel Block B — Maggi & Drinks)...")
        munch9 = GroupOrder(
            id="group-munch9-demo",
            invite_code="MUNCH9",
            title="Hostel Block B — Maggi & Drinks",
            host_name="Bhavya",
            store_mode="late_night_snacks",
            delivery_location="Hostel Block B, Room 304",
            cart_status="OPEN",
            fee_policy="EQUAL_SPLIT",
            delivery_fee_paise=4000,
            platform_fee_paise=1000,
            packaging_fee_paise=1500,
            tax_percentage=5.0,
            is_payment_required_before_finalize=True,
            host_approval_required=False,
            allow_participant_edit=True
        )
        db.add(munch9)
        db.flush()

        p_bhavya = GroupParticipant(
            id="part-munch9-bhavya",
            group_order_id=munch9.id,
            display_name="Bhavya (Host)",
            avatar_color="#FF5C00",
            is_host=True,
            payment_status="PAID",
            amount_paid_paise=4525
        )
        p_sneha = GroupParticipant(
            id="part-munch9-sneha",
            group_order_id=munch9.id,
            display_name="Sneha",
            avatar_color="#EC4899",
            is_host=False,
            payment_status="PAID",
            amount_paid_paise=28725
        )
        p_rohan = GroupParticipant(
            id="part-munch9-rohan",
            group_order_id=munch9.id,
            display_name="Rohan",
            avatar_color="#3B82F6",
            is_host=False,
            payment_status="PAID",
            amount_paid_paise=5725
        )
        p_aman = GroupParticipant(
            id="part-munch9-aman",
            group_order_id=munch9.id,
            display_name="Aman",
            avatar_color="#10B981",
            is_host=False,
            payment_status="PENDING",
            amount_paid_paise=0
        )
        db.add_all([p_bhavya, p_sneha, p_rohan, p_aman])
        db.flush()

        m9_items = [
            CartItem(id="item-m9-1", group_order_id=munch9.id, participant_id=p_bhavya.id, product_id="prod-maggi-masala", quantity=2, unit_price_paise=1400),
            CartItem(id="item-m9-2", group_order_id=munch9.id, participant_id=p_sneha.id, product_id="prod-buldak-2x", quantity=1, unit_price_paise=14500),
            CartItem(id="item-m9-3", group_order_id=munch9.id, participant_id=p_sneha.id, product_id="prod-redbull", quantity=1, unit_price_paise=12500),
            CartItem(id="item-m9-4", group_order_id=munch9.id, participant_id=p_rohan.id, product_id="prod-lays-magic", quantity=2, unit_price_paise=2000),
            CartItem(id="item-m9-5", group_order_id=munch9.id, participant_id=p_aman.id, product_id="prod-amul-taaza-milk", quantity=1, unit_price_paise=3700),
        ]
        db.add_all(m9_items)
        db.flush()

        db.add(AuditLog(
            id=str(uuid.uuid4()),
            group_order_id=munch9.id,
            action="GROUP_CREATED",
            actor_type="HOST",
            actor_name="Bhavya",
            details_json='{"message": "Host created group order MUNCH9"}'
        ))

        calculate_group_bill(munch9, db)
        db.commit()
        print("MUNCH9 seeded successfully!")

    # 2. Seed EXAM26
    exam26 = db.query(GroupOrder).filter(GroupOrder.invite_code == "EXAM26").first()
    if not exam26:
        print("Seeding demo group EXAM26 (Midnight Study Session Snacks)...")
        exam26 = GroupOrder(
            id="group-exam26-demo",
            invite_code="EXAM26",
            title="Midnight Study Session Snacks",
            host_name="Kabir",
            store_mode="late_night_snacks",
            delivery_location="Study Room 2",
            cart_status="LOCKED",
            fee_policy="EQUAL_SPLIT",
            delivery_fee_paise=4000,
            platform_fee_paise=1000,
            packaging_fee_paise=1500,
            tax_percentage=5.0,
            is_payment_required_before_finalize=True,
            host_approval_required=False,
            allow_participant_edit=True
        )
        db.add(exam26)
        db.flush()

        p_kabir = GroupParticipant(
            id="part-exam-kabir",
            group_order_id=exam26.id,
            display_name="Kabir (Host)",
            avatar_color="#8B5CF6",
            is_host=True,
            payment_status="PAID",
            amount_paid_paise=31245
        )
        p_ananya = GroupParticipant(
            id="part-exam-ananya",
            group_order_id=exam26.id,
            display_name="Ananya",
            avatar_color="#EC4899",
            is_host=False,
            payment_status="PAID",
            amount_paid_paise=10245
        )
        p_vikram = GroupParticipant(
            id="part-exam-vikram",
            group_order_id=exam26.id,
            display_name="Vikram",
            avatar_color="#F59E0B",
            is_host=False,
            payment_status="PAID",
            amount_paid_paise=11245
        )
        db.add_all([p_kabir, p_ananya, p_vikram])
        db.flush()

        ex_items = [
            CartItem(id="item-ex-1", group_order_id=exam26.id, participant_id=p_kabir.id, product_id="prod-redbull", quantity=2, unit_price_paise=12500),
            CartItem(id="item-ex-2", group_order_id=exam26.id, participant_id=p_kabir.id, product_id="prod-maggi-special", quantity=2, unit_price_paise=2000),
            CartItem(id="item-ex-3", group_order_id=exam26.id, participant_id=p_ananya.id, product_id="prod-kurkure-munch", quantity=2, unit_price_paise=2000),
            CartItem(id="item-ex-4", group_order_id=exam26.id, participant_id=p_ananya.id, product_id="prod-thums-up", quantity=1, unit_price_paise=4000),
            CartItem(id="item-ex-5", group_order_id=exam26.id, participant_id=p_vikram.id, product_id="prod-doritos-cheese", quantity=1, unit_price_paise=5000),
            CartItem(id="item-ex-6", group_order_id=exam26.id, participant_id=p_vikram.id, product_id="prod-coke-zero", quantity=1, unit_price_paise=4000),
        ]
        db.add_all(ex_items)
        db.flush()

        db.add(AuditLog(
            id=str(uuid.uuid4()),
            group_order_id=exam26.id,
            action="GROUP_LOCKED",
            actor_type="HOST",
            actor_name="Kabir",
            details_json='{"message": "Host locked cart for payments"}'
        ))

        calculate_group_bill(exam26, db)
        db.commit()
        print("EXAM26 seeded successfully!")


def seed_database():
    """Seeds the database with rich product categories and authentic late-night snacks."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Check if products already seeded
        if db.query(ProductCategory).count() > 0:
            print("Database already contains product categories. Skipping product seed.")
            seed_demo_groups(db)
            return

        print("Seeding MunchMate database with late-night food, snacks & groceries...")

        categories = [
            ProductCategory(id="noodles", name="Instant Noodles", slug="instant-noodles", icon="Soup", display_order=1),
            ProductCategory(id="chips", name="Chips & Savouries", slug="chips-and-savouries", icon="Sparkles", display_order=2),
            ProductCategory(id="drinks", name="Cold Drinks & Energy", slug="cold-drinks", icon="GlassWater", display_order=3),
            ProductCategory(id="chocolates", name="Chocolates & Sweets", slug="chocolates-and-sweets", icon="Heart", display_order=4),
            ProductCategory(id="biscuits", name="Biscuits & Cookies", slug="biscuits-and-cookies", icon="Cookie", display_order=5),
            ProductCategory(id="coffee-tea", name="Tea & Cold Coffee", slug="tea-and-coffee", icon="Coffee", display_order=6),
            ProductCategory(id="bakery", name="Bakery & Desserts", slug="bakery-and-desserts", icon="Cake", display_order=7),
            ProductCategory(id="dairy", name="Dairy & Eggs", slug="dairy-and-eggs", icon="Milk", display_order=8),
            ProductCategory(id="essentials", name="Hostel Essentials", slug="hostel-essentials", icon="ShoppingBag", display_order=9),
        ]

        for cat in categories:
            db.add(cat)
        db.flush()

        products = [
            # Instant Noodles
            Product(
                id="prod-maggi-masala",
                category_id="noodles",
                name="Maggi 2-Minute Masala Noodles",
                description="The quintessential hostel fuel. Spicy masala taste with authentic spices.",
                price_paise=1400, # ₹14.00
                image_url="https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="70g pack",
                popularity_score=99
            ),
            Product(
                id="prod-maggi-special",
                category_id="noodles",
                name="Maggi Special Masala Noodles (Spicy)",
                description="Infused with 20 roasted ground spices for an intense late-night kick.",
                price_paise=2000, # ₹20.00
                image_url="https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="70g pack",
                popularity_score=88
            ),
            Product(
                id="prod-buldak-2x",
                category_id="noodles",
                name="Samyang Buldak 2X Spicy Hot Chicken",
                description="Extreme Korean spicy stir-fried ramen. For the bold night owls.",
                price_paise=14500, # ₹145.00
                image_url="https://images.unsplash.com/photo-1552611052-33e04de081de?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=False,
                unit="140g pack",
                popularity_score=92
            ),
            Product(
                id="prod-wai-wai",
                category_id="noodles",
                name="Wai Wai Ready to Eat Chicken Noodles",
                description="Eat raw as crunchy snack or boil in 2 minutes. Hostel classic.",
                price_paise=2500, # ₹25.00
                image_url="https://images.unsplash.com/photo-1594834749740-74b3f6764be4?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=False,
                unit="70g pack",
                popularity_score=85
            ),
            Product(
                id="prod-yippee",
                category_id="noodles",
                name="Sunfeast YiPPee! Magic Masala",
                description="Non-sticky, round round noodles that never get clumped.",
                price_paise=1400, # ₹14.00
                image_url="https://images.unsplash.com/photo-1612927601601-6638404737ce?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="65g pack",
                popularity_score=78
            ),

            # Chips & Savouries
            Product(
                id="prod-kurkure-munch",
                category_id="chips",
                name="Kurkure Masala Munch Crunchy Snacks",
                description="Tedha hai par mera hai! Crispy spice-blended rice and corn puffs.",
                price_paise=2000, # ₹20.00
                image_url="https://images.unsplash.com/photo-1566478989037-eec170784d0b?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="75g pack",
                popularity_score=98
            ),
            Product(
                id="prod-lays-magic",
                category_id="chips",
                name="Lay's India's Magic Masala Potato Chips",
                description="Signature spicy blue Lay's with aromatic northern Indian spice blend.",
                price_paise=2000, # ₹20.00
                image_url="https://images.unsplash.com/photo-1527842891421-42eec6e703ea?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="50g pack",
                popularity_score=97
            ),
            Product(
                id="prod-doritos-cheese",
                category_id="chips",
                name="Doritos Nacho Cheese Tortilla Chips",
                description="Triangular crunch with mouth-melting bold cheesy taste.",
                price_paise=5000, # ₹50.00
                image_url="https://images.unsplash.com/photo-1599490659213-e2b9527bd087?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="75g pack",
                popularity_score=89
            ),
            Product(
                id="prod-haldiram-bhujia",
                category_id="chips",
                name="Haldiram's Nagpur Aloo Bhujia",
                description="Crispy potato & gram flour noodles spiced with red chilli & mint.",
                price_paise=4800, # ₹48.00
                image_url="https://images.unsplash.com/photo-1621996346565-e3d5d6281140?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="150g pack",
                popularity_score=91
            ),

            # Cold Drinks & Energy
            Product(
                id="prod-redbull",
                category_id="drinks",
                name="Red Bull Energy Drink",
                description="Vitalizes body and mind. The essential companion for all-nighters.",
                price_paise=12500, # ₹125.00
                image_url="https://images.unsplash.com/photo-1551024709-8f23befc6f87?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="250ml can",
                popularity_score=96
            ),
            Product(
                id="prod-thums-up",
                category_id="drinks",
                name="Thums Up Charged Carbonated Beverage",
                description="Taste the Thunder! Strong fizz with an intense cola punch.",
                price_paise=4000, # ₹40.00
                image_url="https://images.unsplash.com/photo-1622483767028-3f66f32aef97?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="300ml can",
                popularity_score=94
            ),
            Product(
                id="prod-coke-zero",
                category_id="drinks",
                name="Coca-Cola Zero Sugar Can",
                description="Classic Coke crisp refreshment with zero calories and zero sugar.",
                price_paise=4000, # ₹40.00
                image_url="https://images.unsplash.com/photo-1554866585-cd94860890b7?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="300ml can",
                popularity_score=84
            ),
            Product(
                id="prod-monster-energy",
                category_id="drinks",
                name="Monster Energy Ultra Paradise",
                description="Zero sugar energy drink with refreshing kiwi and lime notes.",
                price_paise=13500, # ₹135.00
                image_url="https://images.unsplash.com/photo-1622543925917-763c34d1a86e?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="350ml can",
                popularity_score=87
            ),

            # Chocolates & Sweets
            Product(
                id="prod-dairy-milk-silk",
                category_id="chocolates",
                name="Cadbury Dairy Milk Silk Oreo",
                description="Creamy smooth milk chocolate filled with crunchy Oreo cookie bits.",
                price_paise=8500, # ₹85.00
                image_url="https://images.unsplash.com/photo-1549007994-cb92caebd54b?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="60g bar",
                popularity_score=93
            ),
            Product(
                id="prod-kitkat-4finger",
                category_id="chocolates",
                name="Nestle KitKat 4 Finger Chocolate Bar",
                description="Crisp wafer fingers coated in smooth milk chocolate. Have a break!",
                price_paise=3000, # ₹30.00
                image_url="https://images.unsplash.com/photo-1541781774459-bb2af2f05b55?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="38g pack",
                popularity_score=90
            ),
            Product(
                id="prod-snickers",
                category_id="chocolates",
                name="Snickers Peanut Chocolate Bar",
                description="Loaded with roasted peanuts, rich caramel, and chewy nougat.",
                price_paise=5000, # ₹50.00
                image_url="https://images.unsplash.com/photo-1582293041079-7814c2f12063?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="50g bar",
                popularity_score=89
            ),

            # Biscuits & Cookies
            Product(
                id="prod-oreo-vanilla",
                category_id="biscuits",
                name="Cadbury Oreo Vanilla Cream Sandwich Cookies",
                description="Rich dark chocolate cookies filled with sweet vanilla creme.",
                price_paise=3500, # ₹35.00
                image_url="https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="120g pack",
                popularity_score=90
            ),
            Product(
                id="prod-hide-and-seek",
                category_id="biscuits",
                name="Parle Hide & Seek Choco Chip Cookies",
                description="Mouth-melting chocolate biscuits loaded with real chocolate chips.",
                price_paise=3000, # ₹30.00
                image_url="https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="100g pack",
                popularity_score=86
            ),

            # Tea & Cold Coffee
            Product(
                id="prod-sleepy-owl-coffee",
                category_id="coffee-tea",
                name="Sleepy Owl Cold Coffee Sweet Can",
                description="Brewed from 100% Arabica beans with fresh toned milk. Ultra smooth.",
                price_paise=11000, # ₹110.00
                image_url="https://images.unsplash.com/photo-1517701550927-30cf4ba1dba5?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="200ml can",
                popularity_score=91
            ),
            Product(
                id="prod-nescafe-cold-latte",
                category_id="coffee-tea",
                name="Nescafe Chilled Latte Can",
                description="Creamy cold coffee can for a refreshing burst of energy.",
                price_paise=4500, # ₹45.00
                image_url="https://images.unsplash.com/photo-1572442388796-11668a67e53d?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="180ml can",
                popularity_score=88
            ),

            # Bakery & Desserts
            Product(
                id="prod-theobroma-brownie",
                category_id="bakery",
                name="Gooey Chocolate Fudge Brownie",
                description="Rich, dense, melted chocolate fudge brownie square.",
                price_paise=9500, # ₹95.00
                image_url="https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="1 slice",
                popularity_score=93
            ),
            Product(
                id="prod-butter-croissant",
                category_id="bakery",
                name="Flaky Golden Butter Croissant",
                description="Freshly baked flaky pastry with 100% French cultured butter.",
                price_paise=7500, # ₹75.00
                image_url="https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="1 piece",
                popularity_score=81
            ),

            # Dairy & Eggs
            Product(
                id="prod-amul-taaza-milk",
                category_id="dairy",
                name="Amul Taaza Toned Milk (Homogenized)",
                description="Long life fresh toned milk in aseptic carton. Perfect for late tea/coffee.",
                price_paise=3700, # ₹37.00
                image_url="https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="500ml pack",
                popularity_score=82
            ),
            Product(
                id="prod-amul-butter",
                category_id="dairy",
                name="Amul Salted Pasteurized Butter",
                description="Utterly butterly delicious! Classic salted yellow table butter.",
                price_paise=5600, # ₹56.00
                image_url="https://images.unsplash.com/photo-1589985270826-4b7bb135bc9d?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="100g pack",
                popularity_score=87
            ),

            # Hostel Essentials
            Product(
                id="prod-paper-napkins",
                category_id="essentials",
                name="Pre-cut Paper Table Napkins (Pack of 100)",
                description="Super absorbent, soft paper tissues for messy late-night munching.",
                price_paise=4000, # ₹40.00
                image_url="https://images.unsplash.com/photo-1584556812952-905ffd0c611a?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="100 sheets",
                popularity_score=75
            ),
            Product(
                id="prod-dettol-sanitizer",
                category_id="essentials",
                name="Dettol Hand Sanitizer Original",
                description="Kills 99.9% germs without water. Essential before eating.",
                price_paise=5000, # ₹50.00
                image_url="https://images.unsplash.com/photo-1584744982491-665216d95f8b?auto=format&fit=crop&w=600&q=80",
                is_available=True,
                is_veg=True,
                unit="50ml bottle",
                popularity_score=79
            ),
        ]

        for p in products:
            db.add(p)

        # Seed a demo registered host user for quick test
        demo_user = User(
            id="user-demo-host",
            email="bhavya@munchmate.dev",
            phone="+919876543210",
            name="Bhavya (Host)",
            hashed_password=get_password_hash("password123"),
            is_active=True
        )
        db.add(demo_user)

        db.commit()
        print(f"Successfully seeded {len(categories)} categories and {len(products)} products!")
        seed_demo_groups(db)

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
