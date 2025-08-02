import argparse
from analysis.user_report import generate_user_report


def main():
    parser = argparse.ArgumentParser(
        description="Generate a weekly fitness report for a single user."
    )
    parser.add_argument(
        "--user_id", "-u",
        required=True,
        help="The user_id to generate the report for"
    )
    parser.add_argument(
        "--output_dir", "-o",
        default="analysis/user_reports",
        help="Directory to write the report Markdown file into"
    )
    args = parser.parse_args()

    # print(f"Generating report for user: {args.user_id}")
    generate_user_report(
        user_id=args.user_id,
        output_dir=args.output_dir
    )


if __name__ == "__main__":
    main()
