import time

# Import the main functions from your report scripts
import overview
import campaign
import campaign_performance
import landing_page
import formfills
import paid_efficiency


def run_all():
    """
    Runs all the report generation scripts sequentially.
    """
    start_time = time.time()
    print("Starting all report generation tasks...")
    print("-" * 40)

    # # --- Generate Paid Efficiency Report ---
    # print("\n[1/6] Generating Paid Efficiency Report...")
    # try:
    #     paid_efficiency.main()
    # except Exception as e:
    #     print(f"  -> ERROR: Failed to generate paid efficiency report: {e}")

    # --- Generate Overview Report (GA) ---
    print("\n[1/5] Generating Overview Report (GA)...")
    try:
        overview.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate overview report: {e}")

    # --- Generate Weekly Campaign Report (GA) ---
    print("\n[2/5] Generating Weekly Campaign Report (GA)...")
    try:
        campaign.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate weekly campaign report: {e}")

    # --- Generate Campaign Performance Report (GA) ---
    print("\n[3/5] Generating Campaign Performance Report (GA)...")
    try:
        campaign_performance.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate campaign performance report: {e}")

    # --- Generate Landing Page Report (GA) ---
    print("\n[4/5] Generating Landing Page Report (GA)...")
    try:
        landing_page.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate landing page report: {e}")

    # --- Generate Form Fills Report (GA) ---
    print("\n[5/5] Generating Form Fills Report (GA)...")
    try:
        formfills.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate form fills report: {e}")

    end_time = time.time()
    print("-" * 40)
    print(f"All reports have been processed in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    run_all()