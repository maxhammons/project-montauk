# Engagement: Accelerator

Futurist, if a test takes 2 hours, no one runs it locally. They push it to CI, they context switch, and they batch their changes. That doesn't prevent overfit garbage; it just means the overfit garbage is shipped in massive, un-reviewable PRs. 

Pragmatist, I am updating my position to incorporate your finding. The 2-hour loop is bad, but the fact that an engineer has to unpack a 10-variable geometric mean to understand *why* the 2-hour loop failed makes it completely unworkable. If we simplify the validation down to what actually matters (hard fails that mean something), we can build a fast-path that engineers actually trust and run.