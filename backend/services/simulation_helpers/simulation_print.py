def print_combo_index_insights(results):
    print("\n=== Combo Index Insights (Average Hits per Combo Index) ===")
    for algo_version, res in results.items():
        combo_hit_stats = [[] for _ in range(8)]
        for date in res["dates"]:
            for idx, combo_result in enumerate(date["combos"]):
                if idx < 8:
                    combo_hit_stats[idx].append(combo_result["hits"])
        print(f"Algorithm: {algo_version}")
        for idx, hits in enumerate(combo_hit_stats):
            avg_hits = sum(hits) / len(hits) if hits else 0
            print(f"  Combo #{{idx+1}}: Avg Hits = {{avg_hits:.2f}} (n={{len(hits)}})")

def print_table_summary(results):
    try:
        from tabulate import tabulate
        use_tabulate = True
    except ImportError:
        use_tabulate = False
    for version, res in results.items():
        print(f"\nAlgorithm: {version}")
        headers = ["Date", "Actual Numbers", "Actual Strong", "Max Hits", "Any Strong Hit", "Total Prize"]
        table = []
        for d in res["dates"]:
            table.append([
                d["test_draw_date"],
                d["actual_numbers"],
                d["actual_strong"],
                d["max_hits"],
                d["any_strong_hit"],
                d["total_prize"]
            ])
        if use_tabulate:
            print(tabulate(table, headers=headers, tablefmt="github"))
        else:
            print(" | ".join(headers))
            for row in table:
                print(" | ".join(str(x) for x in row))
        print(f"Total Prize: {res['total_prize']}, Total Cost: {res['total_cost']}, ROI: {res['roi']}")
        print_combo_index_insights(results) 