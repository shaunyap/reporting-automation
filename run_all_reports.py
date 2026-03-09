import time

# Import the main functions from your report scripts
import overview
import campaign
import campaign_performance
import landing_page
import weekly_conversions
import formfills

def run_all():
    """
    Runs all the report generation scripts sequentially.
    """
    start_time = time.time()
    print("Starting all report generation tasks...")
    print("-" * 40)

    # --- Generate Overview Report (GA) ---
    print("\n[1/6] Generating Overview Report (GA)...")
    try:
        overview.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate overview report: {e}")

    # --- Generate Weekly Campaign Report (GA) ---
    print("\n[2/6] Generating Weekly Campaign Report (GA)...")
    try:
        campaign.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate weekly campaign report: {e}")

    # --- Generate Campaign Performance Report (GA) ---
    print("\n[3/6] Generating Campaign Performance Report (GA)...")
    try:
        campaign_performance.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate campaign performance report: {e}")

    # --- Generate Landing Page Report (GA) ---
    print("\n[4/6] Generating Landing Page Report (GA)...")
    try:
        landing_page.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate landing page report: {e}")

    # --- Generate Form Fills Report (GA) ---
    print("\n[5/6] Generating Form Fills Report (GA)...")
    try:
        formfills.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate form fills report: {e}")

    # --- Generate Weekly Conversions Report (GA) ---
    print("\n[6/6] Generating Weekly Conversions Report (GA)...")
    try:
        weekly_conversions.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate weekly conversions report: {e}")

    end_time = time.time()
    print("-" * 40)
    print(f"All reports have been processed in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    run_all()