import time
import cv2
import numpy
import logging


logger = logging.getLogger('indi_allsky')



class IndiAllskyDetectLines(object):

    canny_low_threshold = 15
    canny_high_threshold = 50

    blur_kernel_size = 5

    rho = 1  # distance resolution in pixels of the Hough grid
    theta = numpy.pi / 180  # angular resolution in radians of the Hough grid
    threshold = 125  # minimum number of votes (intersections in Hough grid cell)
    min_line_length = 40  # minimum number of pixels making up a line
    max_line_gap = 20  # maximum gap in pixels between connectable line segments

    mask_blur_kernel_size = 7


    def __init__(self, config, bin_v, mask=None):
        self.config = config
        self.bin_v = bin_v

        self._sqm_mask = mask


    def detectLines(self, original_img):
        if isinstance(self._sqm_mask, type(None)):
            # This only needs to be done once if a mask is not provided
            self._generateSqmMask(original_img)

        masked_img = cv2.bitwise_and(original_img, original_img, mask=self._sqm_mask)


        if len(original_img.shape) == 2:
            img_gray = masked_img
        else:
            img_gray = cv2.cvtColor(masked_img, cv2.COLOR_BGR2GRAY)



        lines_start = time.time()

        blur_gray = cv2.GaussianBlur(img_gray, (self.blur_kernel_size, self.blur_kernel_size), 0)


        edges = cv2.Canny(blur_gray, self.canny_low_threshold, self.canny_high_threshold)

        # Run Hough on edge detected image
        # Output "lines" is an array containing endpoints of detected line segments
        lines = cv2.HoughLinesP(
            edges,
            self.rho,
            self.theta,
            self.threshold,
            numpy.array([]),
            self.min_line_length,
            self.max_line_gap,
        )

        lines_elapsed_s = time.time() - lines_start
        logger.info('Line detection in %0.4f s', lines_elapsed_s)

        if isinstance(lines, type(None)):
            logger.info('Detected 0 lines')
            return list()


        logger.info('Detected %d lines', len(lines))

        self._drawLines(original_img, lines)

        return lines


    def _generateSqmMask(self, img):
        logger.info('Generating mask based on SQM_ROI')

        image_height, image_width = img.shape[:2]

        # create a black background
        mask = numpy.zeros((image_height, image_width), dtype=numpy.uint8)

        sqm_roi = self.config.get('SQM_ROI', [])

        try:
            x1 = int(sqm_roi[0] / self.bin_v.value)
            y1 = int(sqm_roi[1] / self.bin_v.value)
            x2 = int(sqm_roi[2] / self.bin_v.value)
            y2 = int(sqm_roi[3] / self.bin_v.value)
        except IndexError:
            logger.warning('Using central ROI for blob calculations')
            x1 = int((image_width / 2) - (image_width / 3))
            y1 = int((image_height / 2) - (image_height / 3))
            x2 = int((image_width / 2) + (image_width / 3))
            y2 = int((image_height / 2) + (image_height / 3))

        # The white area is what we keep
        cv2.rectangle(
            img=mask,
            pt1=(x1, y1),
            pt2=(x2, y2),
            color=(255, 255, 255),
            thickness=cv2.FILLED,
        )

        # mask needs to be blurred so that we do not detect it as an edge
        self._sqm_mask = cv2.blur(src=mask, ksize=(self.mask_blur_kernel_size, self.mask_blur_kernel_size))


    def _drawLines(self, img, lines):
        if not self.config.get('DETECT_DRAW'):
            return

        color_bgr = list(self.config['TEXT_PROPERTIES']['FONT_COLOR'])
        color_bgr.reverse()


        for line in lines:
            for x1, y1, x2, y2 in line:
                cv2.line(
                    img,
                    (x1, y1),
                    (x2, y2),
                    tuple(color_bgr),
                    3,
                )

