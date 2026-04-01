# User And Game Mapping Design

## Why This Exists

The bot facade can safely move `stats` and `gene` flows onto the refactored stack because those flows already have stable application DTOs and do not depend on legacy integer primary keys at runtime.

`user` and `game` are different:

- legacy `src.app` uses integer primary keys
- refactored `src.domain` and `src.infrastructure` use UUID-based identities
- legacy game sessions reference `gene_id`
- refactored game sessions store the guessed `word` and do not keep `gene_id`

Because of that, user/game translation must use explicit bridge rules rather than ad-hoc casts.

## Current Model Mismatch

### User

Legacy model:

- table: `users`
- primary key: `id: int`
- stable external key: `telegram_id: int`
- mutable fields used by bot: `username`, `full_name`, `energy`, `total_points`

Refactored model:

- table: `users`
- primary key: `id: UUID`
- stable external key: `telegram_id: int`
- mutable fields used by application: `username`, `full_name`, `energy`, `total_points`

Conclusion:

- `telegram_id` is the only safe cross-model identity key.
- `legacy user.id` must never be converted into UUID mechanically.
- `refactored user.id` must never be truncated or hashed into int.

### Game

Legacy model:

- table: `game_sessions`
- primary key: `id: int`
- owner key: `user_id: int`
- puzzle key: `gene_id: int`
- progress fields: `attempts`, `max_attempts`, `is_won`, `is_finished`, `hint_used`, `points_earned`
- timestamps: `started_at`, `finished_at`

Refactored model:

- table: `game_sessions`
- primary key: `id: UUID string`
- owner key: `user_id: UUID`
- puzzle key: `word: str`
- progress fields: `attempts_count`, `max_attempts`, `is_won`, `is_finished`, `hint_used`, `points_earned`
- timestamps: `created_at`, `finished_at`

Conclusion:

- there is no durable `legacy gene_id -> new game.gene_id` mapping because the new game model does not store `gene_id`
- the canonical bridge for the puzzle itself is `gene.name == game.word`
- a game bridge must carry both user identity mapping and puzzle-word mapping

## Required Bridge Objects

### UserIdentityBridge

Recommended runtime object:

```python
@dataclass(frozen=True)
class UserIdentityBridge:
    telegram_id: int
    legacy_user_id: int | None
    domain_user_id: UUID | None
    username: str | None
    full_name: str | None
```

Resolution rule:

- load legacy user by `telegram_id`
- load refactored user by `telegram_id`
- if one side is missing, create it explicitly in that side's own layer
- return both identifiers together

### GameSessionBridge

Recommended runtime object:

```python
@dataclass(frozen=True)
class GameSessionBridge:
    telegram_id: int
    legacy_game_id: int | None
    domain_game_id: UUID | None
    legacy_gene_id: int | None
    domain_gene_id: UUID | None
    gene_name: str
    is_finished: bool
```
```

Resolution rule:

- resolve user first through `UserIdentityBridge`
- resolve gene by canonical `gene_name`
- match active game by `(telegram_id, gene_name, is_finished=False)`
- only use direct ID lookup after the bridge object has been built

## Canonical Mapping Rules

### User Mapping

1. Canonical external identity is `telegram_id`.
2. `legacy_user_id` is only for legacy services and ORM writes.
3. `domain_user_id` is only for application/repository use cases.
4. Bot middleware should eventually inject a richer user context containing both IDs.

### Gene Mapping For Game Flows

1. Canonical cross-stack gene identity is `gene.name.upper()`.
2. Legacy game flows may still require `legacy_gene_id`.
3. Refactored game flows should use `domain_gene_id` when selecting a gene, but store `gene.name` in the resulting game session.
4. Never infer `domain_gene_id` from `legacy_gene_id` without a repository lookup.

### Game Mapping

1. Do not convert `legacy_game_id` to UUID or reverse.
2. When both stacks coexist, map games by:
   - resolved user bridge
   - canonical `gene_name`
   - active/finished state
   - closest matching creation day when needed
3. If deterministic cross-stack correlation is required, introduce a dedicated bridge table instead of heuristic lookup.

## Recommended Persistence Strategy

If user/game migration continues beyond read-only bridging, add explicit bridge tables.

### `user_identity_bridge`

Columns:

- `telegram_id BIGINT PRIMARY KEY`
- `legacy_user_id BIGINT NULL UNIQUE`
- `domain_user_id UUID NULL UNIQUE`
- `created_at TIMESTAMP NOT NULL`
- `updated_at TIMESTAMP NOT NULL`

### `game_session_bridge`

Columns:

- `id UUID PRIMARY KEY`
- `telegram_id BIGINT NOT NULL`
- `legacy_game_id BIGINT NULL UNIQUE`
- `domain_game_id UUID NULL UNIQUE`
- `legacy_gene_id INT NULL`
- `domain_gene_id UUID NULL`
- `gene_name VARCHAR NOT NULL`
- `bridge_state VARCHAR NOT NULL`
- `created_at TIMESTAMP NOT NULL`
- `updated_at TIMESTAMP NOT NULL`

This avoids hidden heuristics in handlers and keeps reconciliation observable.

## Migration Sequence

### Phase 1

- keep bot gameplay on legacy user/game services
- move supporting flows like `stats` and `gene` to refactored application layer
- add runtime bridge objects in the facade

### Phase 2

- introduce `UserIdentityBridge`
- make middleware inject both legacy and domain identifiers
- move bot user reads to application queries keyed by `telegram_id`

### Phase 3

- introduce `GameSessionBridge`
- resolve game selection through `(telegram_id, gene_name)`
- migrate start/submit/surrender flows one by one

### Phase 4

- remove legacy game service usage from bot facade
- delete bridge code that is no longer needed after full cutover

## Immediate Next Implementation Target

The next safe implementation step is:

- add a bot-facing user context that carries both `telegram_id` and `domain_user_id`
- keep legacy `user.id` only while `energy`, `hint`, and legacy gameplay still depend on it
- start game migration only after the user bridge exists and gene identity is normalized by `gene.name`
