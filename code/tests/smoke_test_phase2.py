"""
Smoke test for Phase 2 components: Vision Extractor and Message Classifier.
Verifies amount extraction from all 16 PNG images and defense classification of all 215 messages.
"""

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_DIR))

import config
from data.loader import load_images, load_messages
from extraction.vision import VisionExtractor
from extraction.messages import MessageClassifier

def run_smoke_test_phase2():
    print("=== STARTING PHASE 2 SMOKE TEST ===")

    # 1. Test Vision Extraction
    print("\n[1] Testing Multimodal Vision Extractor...")
    vision = VisionExtractor()
    images = load_images(config.IMAGES_CSV)
    event_amount_map = vision.get_event_amount_map(config.IMAGES_CSV)
    
    print(f"  Total images processed: {len(images)}")
    print(f"  Events with extracted amounts: {len(event_amount_map)} (expected 16)")
    assert len(event_amount_map) == 16, f"Expected 16 extracted event amounts, got {len(event_amount_map)}"

    print("\n  Sample Vision Extractions:")
    for img in images[:5]:
        data = vision.extract_amount(img.image_id)
        print(f"    - {img.image_id} -> {img.related_event_id}: {data['amount']} {data['currency']} ({data.get('description', '')})")
        assert data["amount"] > 0, f"Expected positive amount for {img.image_id}"

    # 2. Test Message Classifier & Adversarial Defense
    print("\n[2] Testing Message Classifier & Adversarial Defense...")
    classifier = MessageClassifier()
    messages = load_messages(config.MESSAGES_CSV)
    effects = classifier.classify_all(messages)
    
    print(f"  Total messages classified: {len(effects)} (expected 215)")
    assert len(effects) == 215

    # Check adversarial scam detection
    scam_67 = effects["message_67"]
    scam_142 = effects["message_142"]
    print(f"  Adversarial check message_67: {scam_67.effect_type} (is_adversarial={scam_67.is_adversarial})")
    print(f"  Adversarial check message_142: {scam_142.effect_type} (is_adversarial={scam_142.is_adversarial})")
    assert scam_67.is_adversarial, "message_67 was not flagged as adversarial!"
    assert scam_142.is_adversarial, "message_142 was not flagged as adversarial!"
    assert not scam_67.should_modify_cashflow
    assert not scam_142.should_modify_cashflow

    # Category breakdown
    category_counts = {}
    for eff in effects.values():
        category_counts[eff.effect_type] = category_counts.get(eff.effect_type, 0) + 1
    
    print("\n  Message Category Breakdown:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"    - {cat:22s}: {count}")

    print("\n==========================================")
    print(" PHASE 2 SMOKE TEST PASSED WITH 100% SUCCESS ")
    print("==========================================")

if __name__ == "__main__":
    run_smoke_test_phase2()
