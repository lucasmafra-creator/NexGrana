import sys
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nex_controller import NexAssetManager, NexEvent, NexStateMachine, State


class NexVivoTests(TestCase):
    def test_golden_asset_is_final_fallback_and_unapproved_asset_is_ignored(self):
        assets=NexAssetManager()
        self.assertEqual(assets.resolve("hero",candidate="inferior.gif",candidate_approved=False),"nex/nex_hero.png")
        self.assertEqual(assets.fallback_chain("avatar")[-1],"nex/nex_hd.png")

    def test_event_changes_visual_state_without_financial_write(self):
        nex=NexStateMachine()
        reaction=nex.handle(NexEvent.INCOME_ADDED,now=10)
        self.assertTrue(reaction.accepted)
        self.assertIn(nex.state,{State.CELEBRATE,State.JUMP,State.COINS})

    def test_event_cooldown_and_state_antirepetition(self):
        nex=NexStateMachine()
        first=nex.handle(NexEvent.INCOME_ADDED,now=10)
        blocked=nex.handle(NexEvent.INCOME_ADDED,now=10.5)
        second=nex.handle(NexEvent.INCOME_ADDED,now=12)
        self.assertTrue(first.accepted)
        self.assertFalse(blocked.accepted)
        self.assertTrue(second.accepted)
        self.assertNotEqual(first.state,second.state)

    def test_disabled_and_reduced_motion_are_safe(self):
        nex=NexStateMachine({"enabled":False})
        self.assertFalse(nex.handle(NexEvent.GOAL_COMPLETED,now=1).accepted)
        nex.configure({"enabled":True,"reduced_motion":True})
        nex.set_state("celebrate")
        self.assertEqual(nex.motion(1),{"scale":1,"rotate":0,"opacity":1,"dx":0,"dy":0})
        nex.configure({"enabled":True,"intensity":"discreet"})
        self.assertEqual(nex.motion(1),{"scale":1,"rotate":0,"opacity":1,"dx":0,"dy":0})

    def test_multi_click_has_progressive_reactions(self):
        nex=NexStateMachine()
        self.assertEqual(nex.click(now=1).state,State.LOOK.value)
        self.assertEqual(nex.click(now=1.1).state,State.BLINK.value)
        self.assertEqual(nex.click(now=1.2).state,State.WAVE.value)
