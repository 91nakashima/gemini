from gemini import GenimiAI
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='GenimiAI')
    parser.add_argument('-q', '--query', help='query', required=True)
    args = parser.parse_args()
    g = GenimiAI()
    res = g.get_anything_chat(args.query)
    print(res)
