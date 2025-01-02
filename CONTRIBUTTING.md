# Contributing Guidelines

Thank you for considering contributing to this project! Follow these guidelines to ensure a smooth and productive collaboration.

---

## **How to Clone the Repository**

To get started, you need to clone the repository to your local machine:

1. **Fork the Repository (Optional for Public Repos):**
   - Navigate to the repository on GitHub and click the **Fork** button in the top-right corner. This will create a copy of the repository under your GitHub account.

2. **Clone the Repository:**
   - Open your terminal or command prompt.
   - Run the following command:
     ```bash
     git clone https://github.com/USERNAME/REPO-NAME.git
     ```
     Replace `USERNAME` with the repository owner’s GitHub username and `REPO-NAME` with the repository name.

3. **Navigate to the Repository Folder:**
   ```bash
   cd REPO-NAME
   ```

4. **Set the Upstream Remote (For Forks Only):**
   - This ensures you can pull updates from the original repository:
     ```bash
     git remote add upstream https://github.com/ORIGINAL-OWNER/REPO-NAME.git
     ```

---

## **How to Submit a Pull Request (PR)**

To contribute changes, follow these steps:

1. **Create a New Branch:**
   - Use a descriptive branch name for your changes:
     ```bash
     git checkout -b feature/your-branch-name
     ```

2. **Make Changes:**
   - Edit files and commit your changes.
   - Use meaningful commit messages:
     ```bash
     git add .
     git commit -m "Add meaningful description of your changes"
     ```

3. **Push Your Changes:**
   - Push the branch to your GitHub repository:
     ```bash
     git push origin feature/your-branch-name
     ```

4. **Open a Pull Request:**
   - Go to the original repository on GitHub.
   - Click the **Pull Requests** tab and then **New Pull Request**.
   - Select your branch and describe your changes.

5. **Respond to Feedback:**
   - Reviewers may request changes. Update your branch as needed and push the updates.

---

## **Guidelines to Avoid Messing with the Main Repository**

1. **Never Commit Directly to the `main` Branch:**
   - Always create a new branch for your changes. This keeps the main branch stable.

2. **Pull the Latest Changes:**
   - Before starting any work, make sure your local `main` branch is up to date:
     ```bash
     git checkout main
     git pull upstream main  # Use 'origin' if you’re working on the original repo
     ```

3. **Resolve Merge Conflicts:**
   - If conflicts arise while pulling updates, carefully resolve them locally before pushing.

4. **Use Draft Pull Requests (Optional):**
   - If your work is in progress but you want feedback, create a draft pull request.

---

## **Additional Notes**

- **Coding Standards:** Follow the coding style and conventions used in this repository. If unclear, refer to existing code.
- **Documentation:** Update or add documentation if your changes affect functionality.
- **Testing:** Ensure your changes are tested and do not break existing functionality.
- **Respect:** Be respectful in all interactions. Constructive feedback is welcome.

---

Thank you for contributing! Let us know if you need any help or clarification.

