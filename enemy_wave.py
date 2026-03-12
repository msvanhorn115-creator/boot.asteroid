import pygame
from enemy import Enemy, SuicideBomber, Harasser, Tank

# Dummy implementation to prevent errors. Replace with real logic as needed.
from enemy_openings import reinforcement_contact
from main import get_persistent_sector_enemies, tune_contact_for_difficulty, spawn_contact_enemy, active_sector

def spawn_enemy_wave(sector, faction, count=2, entry_mode="offscreen"):
    pack = get_persistent_sector_enemies(sector)
    contacts = pack.get("contacts", [])
    for _ in range(max(1, int(count))):
        new_contact = reinforcement_contact(1337, sector, contacts, allow_tank=True)  # TODO: use real world_seed
        new_contact = tune_contact_for_difficulty(new_contact)
        new_contact["faction"] = faction
        new_contact["entry_mode"] = entry_mode
        contacts.append(new_contact)
        if sector == active_sector:
            spawn_contact_enemy(new_contact)
