<script lang="ts">
  import type { GameStore } from '$stores/gameStore.svelte';
  import type { CustomPgnMove } from '$Types/ChessStructs';
  import { getContext, tick } from 'svelte';
  import { cleanComment } from '$features/pgn/pgnParsing';

  /*
   * Front side comments (Puzzle/Study): intro comment, comments of the moves
   * played so far and the comment of a wrong move matching a PGN variation.
   */

  const gameStore = getContext<GameStore>('GAME_STORE');

  type Entry = { key: string; label?: string; text: string; wrong?: boolean };

  let container = $state<HTMLDivElement>();

  function moveLabel(move: CustomPgnMove): string {
    const fullMove = move.before.split(' ')[5] ?? '';
    return `${fullMove}${move.turn === 'b' ? '...' : '.'} ${move.notation.notation}`;
  }

  const entries = $derived.by(() => {
    const list: Entry[] = [];
    const intro = cleanComment(gameStore.rootGame?.gameComment?.comment);
    if (intro) list.push({ key: 'intro', text: intro });

    for (const move of gameStore.pathMoves) {
      const key = move.pgnPath.join(',');
      const before = cleanComment(move.commentMove);
      if (before) list.push({ key: `${key}-before`, text: before });
      const after = cleanComment(move.commentAfter);
      if (after) list.push({ key, label: moveLabel(move), text: after });
    }

    if (gameStore.wrongMoveComment) {
      list.push({ key: 'wrong', text: gameStore.wrongMoveComment, wrong: true });
    }
    return list;
  });

  // Keep the latest comment in view
  $effect(() => {
    entries.length;
    tick().then(() =>
      container?.lastElementChild?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }),
    );
  });
</script>

{#if entries.length}
  <div class="puzzleComments" bind:this={container}>
    {#each entries as entry (entry.key)}
      <p class="entry" class:wrong={entry.wrong}>
        {#if entry.label}<span class="label">{entry.label}</span>{/if}
        {entry.text}
      </p>
    {/each}
  </div>
{/if}

<style lang="scss">
  .puzzleComments {
    padding: 0.5em 0.75em;
    font-size: 1.1em;
    line-height: 1.4;

    .entry {
      margin: 0 0 0.6em;
      white-space: pre-line;

      &:last-child {
        margin-bottom: 0;
      }

      .label {
        font-weight: bold;
        margin-right: 0.4em;
      }

      &.wrong {
        border-left: 3px solid var(--status-fail);
        padding-left: 0.5em;
      }
    }
  }
</style>
