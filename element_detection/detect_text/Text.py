import cv2
import numpy as np
import element_detection.detect_compo.lib_ip.ip_preprocessing as pre


class Text:
    def __init__(self, id, content, location):
        self.id = id
        self.content = content
        self.location = location

        self.width = self.location['right'] - self.location['left']
        self.height = self.location['bottom'] - self.location['top']
        self.center = ((self.location['right'] + self.location['left']) // 2, (self.location['bottom'] + self.location['top']) // 2)
        self.area = self.width * self.height
        self.word_width = self.width / len(self.content)
        self.clip = None

    '''
    ********************************
    *** Relation with Other text ***
    ********************************
    '''
    def reset_location(self, location):
        self.location = location
        self.width = self.location['right'] - self.location['left']
        self.height = self.location['bottom'] - self.location['top']
        self.center = ((self.location['right'] + self.location['left']) // 2, (self.location['bottom'] + self.location['top']) // 2)
        self.area = self.width * self.height
        self.word_width = self.width / len(self.content)

    def is_justified(self, ele_b, direction='h', max_bias_justify=4):
        '''
        Check if the element is justified
        :param max_bias_justify: maximum bias if two elements to be justified
        :param direction:
             - 'v': vertical up-down connection
             - 'h': horizontal left-right connection
        '''
        l_a = self.location
        l_b = ele_b.location
        # connected vertically - up and below
        if direction == 'v':
            # left and right should be justified
            if abs(l_a['left'] - l_b['left']) < max_bias_justify and abs(l_a['right'] - l_b['right']) < max_bias_justify:
                return True
            return False
        elif direction == 'h':
            # top and bottom should be justified
            if abs(l_a['top'] - l_b['top']) < max_bias_justify and abs(l_a['bottom'] - l_b['bottom']) < max_bias_justify:
                return True
            return False

    def is_on_same_line(self, text_b, direction='h', bias_gap=4, bias_justify=4):
        '''
        Check if the element is on the same row(direction='h') or column(direction='v') with ele_b
        :param direction:
             - 'v': vertical up-down connection
             - 'h': horizontal left-right connection
        :return:
        '''
        l_a = self.location
        l_b = text_b.location
        # connected vertically - up and below
        if direction == 'v':
            # left and right should be justified
            if self.is_justified(text_b, direction='v', max_bias_justify=bias_justify):
                # top and bottom should be connected (small gap)
                if abs(l_a['bottom'] - l_b['top']) < bias_gap or abs(l_a['top'] - l_b['bottom']) < bias_gap:
                    return True
            return False
        elif direction == 'h':
            # top and bottom should be justified
            if self.is_justified(text_b, direction='h', max_bias_justify=bias_justify):
                # top and bottom should be connected (small gap)
                if abs(l_a['right'] - l_b['left']) < bias_gap or abs(l_a['left'] - l_b['right']) < bias_gap:
                    return True
            return False

    def is_intersected(self, text_b, bias):
        l_a = self.location
        l_b = text_b.location
        left_in = max(l_a['left'], l_b['left']) - bias
        top_in = max(l_a['top'], l_b['top']) - bias
        right_in = min(l_a['right'], l_b['right'])
        bottom_in = min(l_a['bottom'], l_b['bottom'])

        w_in = max(0, right_in - left_in)
        h_in = max(0, bottom_in - top_in)
        area_in = w_in * h_in
        if area_in > 0:
            return True

    def calc_intersection_area(self, text_b, bias=(0,0)):
        '''
        Calculate the intersection area between the two texts
        '''
        l_a = self.location
        l_b = text_b.location

        col_min_s = max(l_a['left'], l_b['left']) - bias[0]
        row_min_s = max(l_a['top'], l_b['top']) - bias[1]
        col_max_s = min(l_a['right'], l_b['right'])
        row_max_s = min(l_a['bottom'], l_b['bottom'])
        w = np.maximum(0, col_max_s - col_min_s)
        h = np.maximum(0, row_max_s - row_min_s)
        inter = w * h

        iou = inter / (self.area + text_b.area - inter)
        ioa = inter / self.area
        iob = inter / text_b.area
        return inter, iou, ioa, iob

    '''
    ***********************
    *** Revise the Text ***
    ***********************
    '''
    def merge_text(self, text_b):
        text_a = self
        top = min(text_a.location['top'], text_b.location['top'])
        left = min(text_a.location['left'], text_b.location['left'])
        right = max(text_a.location['right'], text_b.location['right'])
        bottom = max(text_a.location['bottom'], text_b.location['bottom'])
        self.location = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
        self.width = self.location['right'] - self.location['left']
        self.height = self.location['bottom'] - self.location['top']
        self.area = self.width * self.height

        left_element = text_a
        right_element = text_b
        if text_a.location['left'] > text_b.location['left']:
            left_element = text_b
            right_element = text_a
        self.content = left_element.content + ' ' + right_element.content
        self.word_width = self.width / len(self.content)

    def shrink_bound(self, binary_map):
        bin_clip = binary_map[self.location['top']:self.location['bottom'], self.location['left']:self.location['right']]
        height, width = np.shape(bin_clip)

        shrink_top = 0
        shrink_bottom = 0
        for i in range(height):
            # top
            if shrink_top == 0:
                if sum(bin_clip[i]) == 0:
                    shrink_top = 1
                else:
                    shrink_top = -1
            elif shrink_top == 1:
                if sum(bin_clip[i]) != 0:
                    self.location['top'] += i
                    shrink_top = -1
            # bottom
            if shrink_bottom == 0:
                if sum(bin_clip[height-i-1]) == 0:
                    shrink_bottom = 1
                else:
                    shrink_bottom = -1
            elif shrink_bottom == 1:
                if sum(bin_clip[height-i-1]) != 0:
                    self.location['bottom'] -= i
                    shrink_bottom = -1

            if shrink_top == -1 and shrink_bottom == -1:
                break

        shrink_left = 0
        shrink_right = 0
        for j in range(width):
            # left
            if shrink_left == 0:
                if sum(bin_clip[:, j]) == 0:
                    shrink_left = 1
                else:
                    shrink_left = -1
            elif shrink_left == 1:
                if sum(bin_clip[:, j]) != 0:
                    self.location['left'] += j
                    shrink_left = -1
            # right
            if shrink_right == 0:
                if sum(bin_clip[:, width-j-1]) == 0:
                    shrink_right = 1
                else:
                    shrink_right = -1
            elif shrink_right == 1:
                if sum(bin_clip[:, width-j-1]) != 0:
                    self.location['right'] -= j
                    shrink_right = -1

            if shrink_left == -1 and shrink_right == -1:
                break
        self.width = self.location['right'] - self.location['left']
        self.height = self.location['bottom'] - self.location['top']
        self.area = self.width * self.height
        self.word_width = self.width / len(self.content)

    def split_letters_in_the_word(self, latest_id):
        '''
        If the gap between two words is too large, split them as different Text
        Only use for word rather than sentence
        :return: list of Text objects
        '''
        # get the binary map of the clip
        binary = pre.binarization(self.clip, 6)

        # check the letters and the gaps between letters
        gaps = []  # gaps between two letters in pixels
        letter_lens = []  # length of letters in pixels
        letter_pos = []  # position of split letters
        black = True
        gap = 0
        letter_len = 0
        start_pos = 0
        start = True
        for i in range(binary.shape[1]):
            # print(int(np.sum(binary[:, i]) / 255))
            # if black pixel
            if int(np.sum(binary[:, i]) / 255) == 0:
                if start:
                    continue
                if not black:
                    letter_lens.append(letter_len)
                    letter_len = 0
                    letter_pos.append((start_pos, i))
                black = True
                gap += 1
            # if white pixel
            else:
                if black and not start:
                    gaps.append(gap)
                    gap = 0
                    start_pos = i
                black = False
                letter_len += 1
                start = False
        if not black:
            letter_lens.append(letter_len)
            letter_pos.append((start_pos, binary.shape[1] - 1))

        # split out letters
        loc = self.location
        split_texts = []
        letters_kept = ''
        left_bound = 0
        for i in range(len(letter_lens) - 1):
            gap = gaps[i]
            pos = letter_pos[i]
            letters_kept += self.content[i]
            if gap > min(letter_lens[i], letter_lens[i + 1]) * 1.5:
                # split out letter
                location = {'top': loc['top'], 'bottom': loc['bottom'],
                            'left': loc['left'] + pos[0], 'right':loc['left'] + pos[1]}
                split_texts.append(Text(latest_id, letters_kept, location))
                left_bound = letter_pos[i + 1][0]
                letters_kept = ''
                latest_id += 1

        self.content = letters_kept + self.content[len(letter_lens) - 1:]
        new_loc = {'top': loc['top'], 'bottom': loc['bottom'],
                   'left': loc['left'] + left_bound, 'right':loc['right']}
        self.reset_location(new_loc)
        split_texts.append(self)
        return split_texts

    '''
    *********************
    *** Visualization ***
    *********************
    '''
    def get_clip(self, img):
        loc = self.location
        self.clip = img[loc['top']:loc['bottom'], loc['left']:loc['right']]

    def visualize_element(self, img, color=(0, 0, 255), line=1, show=False):
        loc = self.location
        cv2.rectangle(img, (loc['left'], loc['top']), (loc['right'], loc['bottom']), color, line)
        if show:
            print(self.content)
            cv2.imshow('text', img)
            cv2.waitKey()
            cv2.destroyWindow('text')
