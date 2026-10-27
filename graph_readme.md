# SCME Dashboard Graphs: A Student-Friendly Guide 📊

Welcome! This guide is designed to explain the **6 interactive 3D charts** on the SCME Dashboard in a very simple, beginner-friendly way. If you are a student, a beginner coder, or an inventory manager, this document will help you understand:
1. **What** each graph is about.
2. **How** it works under the hood.
3. **A simple everyday analogy** to help it click.

---

## 1. Productive Analysis (3D Grouped Bar Chart)
### What it is
This chart compares three main quantities side-by-side for each military unit:
*   **Authorized Scale**: How much equipment the unit is officially supposed to have.
*   **Held**: How much equipment the unit actually has in their warehouse right now.
*   **Deficiency**: How much equipment is missing (Authorized - Held).

### Everyday Analogy 🎒
Imagine you are packing your backpack for school:
*   Your school checklist says you need **10 Notebooks** (Authorized).
*   You check your room and find you have **7 Notebooks** (Held).
*   This means you are missing **3 Notebooks** (Deficiency).
This chart displays these 3 values side-by-side for each unit.

---

## 2. Global Fulfillment (3D Donut Chart)
### What it is
This is a circular donut chart showing the overall percentage of total authorized equipment that is currently in stock across the entire system.

### Everyday Analogy 🍕
Imagine a giant pizza:
*   The whole pizza represents all the equipment authorized across the entire military base.
*   The green slices represent the pizza we actually have (Held).
*   The red slices represent the missing pieces we still need to get (Deficiency).
*   The percentage in the center tells you how much of the pizza is ready.

---

## 3. Top 5 Deficient Items (3D Horizontal Bar Chart)
### What it is
This chart ranks the **5 specific items** that have the highest total shortages (deficiencies) across the entire system.

### Everyday Analogy 📚
If you are running a school bookstore, you want to know which books are out of stock the most so you can order them first. This horizontal chart ranks the top 5 items that have the largest shortages. It helps managers prioritize what to buy first.

---

## 4. Deficiency Share by Unit (3D Pie Chart)
### What it is
This pie chart displays what percentage of the *total system shortage* belongs to each individual unit.

### Everyday Analogy 🍕
Imagine a group project where the team is missing \$100 total to buy supplies:
*   If **Student A** forgot \$50, **Student B** forgot \$30, and **Student C** forgot \$20.
*   Student A is responsible for **50% of the team's shortage**.
This chart shows which unit is responsible for the largest share of the overall deficiency.

---

## 5. Accounting Unit (A/U) Quantity Split (3D Column Chart)
### What it is
This breaks down the total stock of held items by how they are measured or counted (called the **Accounting Unit** or **A/U**):
*   **Nos (Nos/Numbers)**: Items counted individually (like jackets, altimeters, helmets).
*   **Prs (Pairs)**: Items counted in pairs (like boots, gloves, insoles).

### Everyday Analogy 👟
If you count your clothes:
*   You count shirts individually (e.g., 5 Shirts = 5 **Nos**).
*   You count socks in pairs (e.g., 3 pairs of socks = 3 **Prs**).
This chart displays how much of the held inventory is counted in single pieces versus pairs.

---

## 6. Supply Readiness by Unit (3D Color-Coded Column Chart)
### What it is
This calculates the supply readiness percentage for each unit ($\frac{\text{Held}}{\text{Authorized}} \times 100$) and color-codes the columns dynamically so users can see unit health at a single glance:
*   🟢 **Green (>= 80%)**: Excellent readiness.
*   🟡 **Amber (50% - 79%)**: Needs improvement.
*   🔴 **Red (< 50%)**: Critical supply state.

### Everyday Analogy 📝
Think of this as report card grades for readiness:
*   An **A** grade (85%) gets a **Green** label (Passed/Ready).
*   A **C** grade (60%) gets a **Yellow** label (Warning/Needs work).
*   An **F** grade (30%) gets a **Red** label (Fail/Critical).
