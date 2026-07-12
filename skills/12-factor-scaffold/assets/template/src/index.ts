import { run, resume, checkpoint } from "./run";

/**
 * Example entry point (factor 11: this is just one trigger — wire the same run()/resume()
 * to Slack, email, cron, HTTP, a queue, etc.). Runs fully offline with the mock brain.
 */
async function main(): Promise<void> {
  // 1. A simple goal that completes end-to-end.
  const result = await run("What is the refund policy?");
  console.log("status:", result.status);
  console.log("answer:", result.finalAnswer);

  // 2. A goal that pauses for a human, then resumes (factors 6, 7, 12).
  const paused = await run("Confirm before deleting the account");
  console.log("\nstatus:", paused.status); // awaiting_human
  const saved = checkpoint(paused); // could be stored anywhere
  const resumed = await resume(saved, "yes, go ahead");
  console.log("status:", resumed.status);
  console.log("answer:", resumed.finalAnswer);
}

main().catch((err) => {
  console.error(err);
  process.exitCode = 1;
});
