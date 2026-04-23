from argon2 import PasswordHasher, Type

from app.shared import security


def test_argon2_password_hasher_parameters_are_explicit():
    assert security._ph.time_cost == 3
    assert security._ph.memory_cost == 65536
    assert security._ph.parallelism == 4
    assert security._ph.hash_len == 32
    assert security._ph.salt_len == 16
    assert security._ph.type is Type.ID


def test_password_needs_rehash_detects_older_parameters():
    legacy_hasher = PasswordHasher(
        time_cost=2,
        memory_cost=65536,
        parallelism=4,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )

    assert security.password_needs_rehash(legacy_hasher.hash("correct horse battery staple")) is True
