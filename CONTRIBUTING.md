# Contributing Guidelines


## Pull Requests

Pull requests are always welcome and appreciated!
Before doing so, please read the following. It will make the
process much more enjoyable for all.


### **Branch!**

In git, branches are cheap!  (and one your best friends)

Before you even start thinking about typing `git commit`, **always** make sure you are on a branch other than `main/master`. This will save you a *lot* of headaches down the road!

It's easy...
```bash
git checkout -B my-awesome-branch-name
```


And... you can do that *after* you've started typing away and saving your work!  Nothing will be lost (`git` would yell at you if it thought so).

Once you're on a separate branch, commit away!


### Intent

A pull request should have a clear goal.  Whether it's fixing something, making something better, etc.

Keep that goal in mind and keep your changes focused on it.
If you see other shiny things you'd like to make better, take a note of it for a future (separate) PR.

If you notice the file you're working on had extra white space that your editor happily removed for you (which *shouldn't* be the case in this repo), that's fine...

**IF**

the *goal* of the PR is "Fix whitespace and line endings".
If that's not your *goal*, then make a note and submit your PR with the nasty whitespace issues as-is.

Then by all means, make a new branch:
```bash
git checkout master
git checkout -B fix-whitespace
```

and feel free to open another pull request to fix that ugly mess.
Then you get two PR's for the price of one!

### Commits

- Commits should be as small as possible.
  - This helps you tackle big changes without being overwhelmed
  - It also makes it easier for reviewers to see the history and understand the context
- The subject line (first line) of the message should be as small as possible.  50 characters is typical.
  - If you need to provide more information, add a blank line below the subject, and add as many lines in the body as needed (wrapped at somewhere around 72 characters wide)
- Sometimes, the commit message is bigger than the code changes it contains, and that's OK!
- Make the subject clear as to what it *does*, not *why* it does it, what file it does it to or anything else.
- If you corrected a syntax error, the commit message could be something like ...
  - `Correct syntax error`

Easy, right? (not always, but you get the idea)

At all costs, please avoid messages like:

- `Update README.md`
- `Update utils.py`
- `More changes`


![1296](https://imgs.xkcd.com/comics/git_commit.png)

This is what we *try* to avoid and there are plenty of [resources](https://chris.beams.io/posts/git-commit/) out there on this subject.



### Coding Style

This project has quite a bit of legacy code and is admittedly lacking in the style department in quite a few places, but some may call it [patina](https://en.wikipedia.org/wiki/Patina) ;)

That being said, it should be fairly obvious within a section or entire module what the "norm" is.  Please *try* to stick to that whenever possible.

If you'd like to use more modern styling conventions, feel free,
just as long as they don't seem out of place with their surroundings.

If your editor automaticaly applies style fixes when you save though, **please please please** turn that off (unless that's your *intent*).

If you **would** like to address coding style issues and make things uniform throughout the entire codebase, feel free to make a new branch (remember, `git checkout -B style-fixes`) do the things and submit a "Coding Style" PR!  (that may be a big change, so maybe let's not try and tackle it right now).
