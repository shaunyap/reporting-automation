import time

# Import the main functions from your report scripts
import overview
import campaign
import campaign_performance
import landing_page
import formfills


def run_all():
    """
    Runs all the report generation scripts sequentially.
    """
    start_time = time.time()
    print("Starting all report generation tasks...")
    print("-" * 40)

    # --- Generate Overview Report ---
    print("\n[1/5] Generating Overview Report...")
    try:
        overview.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate overview report: {e}")

    # --- Generate Weekly Campaign Report ---
    print("\n[2/5] Generating Weekly Campaign Report...")
    try:
        campaign.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate weekly campaign report: {e}")

    # --- Generate Campaign Performance Report ---
    print("\n[3/5] Generating Campaign Performance Report...")
    try:
        campaign_performance.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate campaign performance report: {e}")

    # --- Generate Landing Page Report ---
    print("\n[4/5] Generating Landing Page Report...")
    try:
        landing_page.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate landing page report: {e}")

    # --- Generate Form Fills Report ---
    print("\n[5/5] Generating Form Fills Report...")
    try:
        formfills.main()
    except Exception as e:
        print(f"  -> ERROR: Failed to generate form fills report: {e}")

    end_time = time.time()
    print("-" * 40)
    print(f"All reports have been processed in {end_time - start_time:.2f} seconds.")


if __name__ == "__main__":
    run_all()