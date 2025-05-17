# 🏴‍☠️ Running Dev & Grid Search on Two GCE Instances (Separate Databases)

This guide shows how to run your development app and grid search on **two separate Google Compute Engine (GCE) instances** for maximum stability, isolation, and reproducibility, with the blessing of the Flying Spaghetti Monster. This version uses **separate databases** for each instance (Option A).

---

## 1. Provision Two GCE Instances

- **Instance 1:** For development (`dev-instance`)
- **Instance 2:** For grid search (`gridsearch-instance`)
- Size each as needed (give `gridsearch-instance` more CPU/RAM if grid search is heavy).

---

## 2. Project Structure & Version Control

- Use a git repository (GitHub, GitLab, etc.) for your code.
- Both instances pull from the same repo.
- Use branches/tags to mark stable code for grid search.

---

## 3. Database Setup (Separate Databases)

- Each instance runs its own database (e.g., Postgres, MySQL, SQLite) on its own disk.
- **Pros:** Total isolation, no risk of dev breaking grid search or vice versa.
- **Cons:** Need to copy data from prod to grid search instance as needed.

---

## 4. Docker Setup on Both Instances

- Both instances use Docker for isolation and reproducibility.
- Each instance has its own `docker-compose.yml` (or just uses `docker run`).

### On dev-instance:
- Mount code as a volume for hot reload.
- Use the dev DB.
- Example:

```yaml
services:
  dev:
    build: .
    volumes:
      - ./backend:/app/backend
    command: python -m flask run --host=0.0.0.0
    ports:
      - "5000:5000"
    environment:
      - ENV=dev
      - DB_URL=postgresql://user:pass@db:5432/lotto_dev
```

### On gridsearch-instance:
- Build Docker image from a stable tag/commit.
- Use the grid search DB.
- No code volume mount (code is frozen in image).
- Example:

```yaml
services:
  gridsearch:
    image: gridsearch:stable
    command: python /app/backend/scripts/grid_search_lstm.py
    environment:
      - ENV=prod
      - DB_URL=postgresql://user:pass@db:5432/lotto_gridsearch
```

---

## 5. Workflow

### A. Development
- Work on `dev-instance` as usual.
- Hot reload, break things, experiment!

### B. Grid Search
- When ready, tag and push stable code to git (e.g., `git tag gridsearch-v1`).
- On `gridsearch-instance`, pull the tag and build the Docker image:
  ```bash
  git fetch --tags
  git checkout gridsearch-v1
  docker build -t gridsearch:stable .
  ```
- Start the grid search container:
  ```bash
  docker run --name gridsearch-run gridsearch:stable
  ```

### C. Data Sync
- Periodically copy production data to the grid search DB on `gridsearch-instance`.
- Use DB dump/restore tools (e.g., `pg_dump`/`pg_restore` for Postgres).

---

## 6. Resource Management

- Each instance can be sized independently.
- No risk of grid search hogging resources from dev, or vice versa.

---

## 7. Logs & Monitoring

- Use Docker logs or write logs to files on each instance.
- Optionally, use centralized logging (e.g., Stackdriver, ELK) for both.

---

## 8. Security

- Restrict network access between instances as needed.
- Use SSH keys for git and instance access.
- Secure DBs with strong passwords and firewalls.

---

## 9. Updating Grid Search Code After Dev Changes

When ye've made changes in yer dev-instance and want to update the code on yer gridsearch-instance, follow these steps:

### Step-by-Step Instructions

1. **Finish and Test Yer Changes in Dev**
   - Make sure yer new code works as expected in yer dev-instance.
   - Commit all yer changes to yer git repo.

2. **Tag the Stable Code for Grid Search**
   - Create a new tag for this version:
     ```bash
     git tag gridsearch-v2
     git push origin gridsearch-v2
     ```
   - (Use a clear, incrementing tag name.)

3. **Go to Yer gridsearch-instance**
   - SSH into yer gridsearch-instance.

4. **Pull the Latest Code and Checkout the Tag**
   ```bash
   git fetch --tags
   git checkout gridsearch-v2
   ```

5. **Build the New Docker Image**
   ```bash
   docker build -t gridsearch:stable .
   ```

6. **Stop the Old Grid Search Container (if runnin')**
   ```bash
   docker stop gridsearch-run
   docker rm gridsearch-run
   ```

7. **Start the New Grid Search Container**
   ```bash
   docker run --name gridsearch-run gridsearch:stable
   ```
   - Or use `docker-compose up gridsearch` if ye be usin' compose.

---

### 🏴‍☠️ Summary Table

| Step                | Command/Action                                 |
|---------------------|------------------------------------------------|
| Commit & tag        | `git tag gridsearch-v2; git push origin gridsearch-v2` |
| On gridsearch-inst. | `git fetch --tags; git checkout gridsearch-v2` |
| Build image         | `docker build -t gridsearch:stable .`          |
| Stop old container  | `docker stop gridsearch-run; docker rm gridsearch-run` |
| Start new container | `docker run --name gridsearch-run gridsearch:stable`   |

---

**Arrr, this way yer grid search always runs on a known, stable code snapshot, and yer dev work never sinks the ship! May the FSM bless yer deployments with smooth seas and bountiful results!**

---

## 🏴‍☠️ Summary Table

| Task                | dev-instance                | gridsearch-instance           |
|---------------------|----------------------------|------------------------------|
| Code                | Live, hot-reload           | Frozen at build/tag           |
| DB                  | lotto_dev                  | lotto_gridsearch              |
| Start Command       | `docker-compose up dev`    | `docker-compose up gridsearch`|
| Update Code         | Edit & reload              | Tag, build, rerun             |
| Resource Isolation  | Full                       | Full                          |

---

**Arrr, with two ships in yer fleet, ye can sail the seas of development and grid search without fear of collision! May the FSM keep yer instances afloat and yer code bug-free.** 