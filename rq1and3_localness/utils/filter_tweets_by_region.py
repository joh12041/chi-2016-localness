"""Split tweets file up by geography (e.g., one file for all tweets in Pennsylvania, one for Ohio, etc.)"""

import csv
import traceback

REGION = "counties"
INPUT_FN = "<PATH NAME TO TWITTER LOCALNESS OUTPUT CSV>"
INPUT_HEADER = ['id', 'created_at', 'text', 'user_screen_name', 'user_description', 'user_lang', 'user_location',
                 'user_time_zone', 'geom_src', 'uid', 'tweet', 'lon', 'lat', 'gender', 'race',
                  'county', 'nday', 'plurality', 'geomed', 'locfield']
OUTPUT_BASE_PATH = "<PATH TO FOLDER THAT WILL CONTAIN PARSED TWEET FILES>"

def process_line(output_line, open_fps, state_files, region, fps):
    if region in open_fps:
        if not open_fps[region]:
            # close oldest fp and open one for the current state/county/region/whatever
            fps[0][1].flush()
            fps[0][1].close()
            open_fps[fps[0][0]] = False
            del(fps[0])
            fout = open(OUTPUT_BASE_PATH + region + '.csv', 'a')
            fps.append([region, fout])
            open_fps[region] = True
            state_files[region] = csv.writer(fout)
        state_files[region].writerow(output_line)
        return 1
    elif region:
        try:
            fout = open(OUTPUT_BASE_PATH + region + '.csv', 'w')
        except Exception:
            # close oldest fp and open new one for current region
            fps[0][1].flush()
            fps[0][1].close()
            open_fps[fps[0][0]] = False
            del(fps[0])
            fout = open(OUTPUT_BASE_PATH + region + '.csv', 'w')
        fps.append([region, fout])
        open_fps[region] = True
        state_files[region] = csv.writer(fout)
        state_files[region].writerow(['text','uid', 'nday','plurality'])
        state_files[region].writerow(output_line)
        return 1
    else:
        return 0


def main():
    region_files = {}
    fps = []
    open_fps = {}
    line_no = 0
    copied_over = 0
    try:
        with open(INPUT_FN, 'r') as fin:
            csvreader = csv.reader(fin)
            assert next(csvreader) == INPUT_HEADER
            geog_idx = INPUT_HEADER.index('county')
            txt_idx = INPUT_HEADER.index('text')
            uid_idx = INPUT_HEADER.index('uid')
            nday_idx = INPUT_HEADER.index('nday')
            plur_idx = INPUT_HEADER.index('plurality')
            for line in csvreader:
                line_no += 1
                try:
                    region = [line[geog_idx]]
                    txt = line[txt_idx]
                    uid = line[uid_idx]
                    n = line[nday_idx]
                    p = line[plur_idx]
                    output_line = [txt, uid, n, p]
                    success = process_line(output_line, open_fps, region_files, region, fps)
                    copied_over += success
                except Exception:
                    continue
                finally:
                    if line_no % 100000 == 0:
                        print("{0} lines processed and {1} copied over for {2} counties.".format(line_no, copied_over, len(open_fps)))
    except Exception:
        traceback.print_exc()
        for fp in fps:
            fp.flush()
            fp.close()


if __name__ == "__main__":
    main()
