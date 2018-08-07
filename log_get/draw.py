"""Summary
"""
import re
import math
import logging

import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('agg')

class LogParser(object):
    """Summary

    Attributes:
        cparser (TYPE): Description
        has_test (bool): Description
        legend (str): Description
        test_gauc_arr (list): Description
        test_iter_arr (list): Description
        test_loss_arr (list): Description
        train_iter_arr (list): Description
        train_loss_arr (list): Description
    """
    def __init__(self, cparser):
        """Summary

        Args:
            cparser (TYPE): Description
        """
        self.cparser = cparser
        self.legend = ""
        self.avg_window_size = 5

        self.train_iter_arr = []
        self.train_loss_arr = []

        self.has_test = False
        self.test_iter_arr = []
        self.test_loss_arr = []
        self.test_gauc_arr = []


    def smooth_list(self, list_in, smooth_window_size):
        list_out = []
        for i in xrange(len(list_in)):
            i_start = max(0, i - smooth_window_size + 1)
            i_end = min(len(list_in), i + 1)
            s = 0.0
            for j in xrange(i_start, i_end):
                 s += list_in[j]

            s /= (i_end - i_start)
            list_out.append(s)
        return list_out


    def parselog(self, filename, legend, max_batch_num = None):
        """Summary

        Args:
            filename (TYPE): Description
            legend (TYPE): Description

        Returns:
            TYPE: Description
        """
        self.legend = legend

        index = 0
        loss_sum = 0.0

        cur_itr = 0



        with open(filename, 'r') as fin:
            line = fin.readline()
            while line:
                result1 = re.findall(r"global_step (\d+) : loss : (.+?)\n$", line)
                result2 = re.findall(r"Test after (\d+) batches", line)
                result3 = re.findall(r"Avg loss : (.+?)\n$", line)
                # result4 = re.findall(r"GAUC : (.+?)\n$", line)
                result4 = re.findall(r"Merged gauc is (.+?)\n$", line)

                if result1:
                    index = int(result1[0][0])
                    loss_sum += float(result1[0][1])

                    if index % self.cparser.train_loss_avg_window == 0:
                        if max_batch_num is None or index <= max_batch_num:
                            self.train_iter_arr.append(index)
                            self.train_loss_arr.append(loss_sum / self.cparser.train_loss_avg_window)
                        loss_sum = 0.0

                elif result2:
                    cur_itr = int(result2[0])
                    if max_batch_num is None or cur_itr <= max_batch_num:
                        self.test_iter_arr.append(int(result2[0]))
                elif result3:
                    if max_batch_num is None or cur_itr <= max_batch_num: 
                        self.test_loss_arr.append(float(result3[0])) 
                elif result4:
                    if max_batch_num is None or cur_itr <= max_batch_num:
                        self.test_gauc_arr.append(float(result4[0]))
                else:
                    pass

                line = fin.readline()

        #print(self.test_iter_arr)
        #print(self.test_loss_arr)
        #print(self.test_gauc_arr)


        if len(self.test_iter_arr) > 0:
            self.has_test = True


        if self.avg_window_size > 1:
            self.test_loss_arr = self.smooth_list(self.test_loss_arr, self.avg_window_size)
            #self.test_gauc_arr = self.smooth_list(self.test_gauc_arr, self.avg_window_size)
            

        # print(self.train_loss_arr)
        # print(self.test_iter_arr)
        # print(self.test_loss_arr)
        # print(self.test_gauc_arr)

class PlotHandler(object):
    """Summary

    Attributes:
        cparser (TYPE): Description
    """
    def __init__(self, cparser):
        """Summary

        Args:
            cparser (TYPE): Description
        """
        self.cparser = cparser

    def draw(self, lparser_list, filename, mode='3column'):
        """Summary

        Returns:
            TYPE: Description

        Args:
            lparser_list (TYPE): Description
            filename (TYPE): Description
            mode (str, optional): Description
        """
        if mode == '3column':
            self.plot_3column(lparser_list, filename)
            logging.info("Result plot has been saved to %s.", filename)

    @staticmethod
    def plot_single(parser, axis, draw_type='Train Loss', loc='upper right'):
        """Summary

        Args:
            parser (TYPE): Description
            axis (TYPE): Description
            draw_type (str, optional): Description
            loc (str, optional): Description

        Returns:
            TYPE: Description
        """
        if draw_type == 'Train Loss':
            if(len(parser.train_iter_arr) > len(parser.train_loss_arr)):
                parser.train_iter_arr = parser.train_iter_arr[:-1]
            axis.plot(parser.train_iter_arr, parser.train_loss_arr,
                      linewidth=0.5, label=parser.legend)
        elif draw_type == 'Test Loss':
            if(len(parser.test_iter_arr) > len(parser.test_loss_arr)):
                parser.test_iter_arr = parser.test_iter_arr[:-1]
            axis.plot(parser.test_iter_arr, parser.test_loss_arr,
                      linewidth=0.5, label=parser.legend)
        elif draw_type == 'Test GAUC':
            if(len(parser.test_iter_arr) > len(parser.test_gauc_arr)):
                parser.test_iter_arr = parser.test_iter_arr[:-1]
            axis.plot(parser.test_iter_arr, parser.test_gauc_arr,
                      linewidth=0.5, label=parser.legend)
        else:
            print("Unknown draw type %s." % draw_type)
            exit(1)

        axis.grid(True)

        ttl = axis.set_title(draw_type, fontsize=18, fontweight='bold')
        ttl.set_position([.5, 1.05])

        axis.set_xlabel('Iteration', fontsize=12, labelpad=12)
        if draw_type == 'Test GAUC':
            axis.set_ylabel('GAUC', fontsize=12, labelpad=12)
        else:
            axis.set_ylabel('Loss', fontsize=12, labelpad=12)

        axis.legend(loc=loc, fontsize=12)

    def plot_3column(self, lparser_list, filename):
        """Summary

        Args:
            lparser_list (TYPE): Description
            filename (TYPE): Description

        Returns:
            TYPE: Description
        """
        fig = plt.figure(figsize=(19, 5))
        fig.subplots_adjust(wspace=0.3)

        # Plot train loss
        axis = fig.add_subplot(131)
        for parser in lparser_list:
            self.plot_single(parser, axis, draw_type='Train Loss')

        axis = fig.add_subplot(132)
        for parser in lparser_list:
            if parser.has_test:
                self.plot_single(parser, axis, draw_type='Test Loss')

        axis = fig.add_subplot(133)
        max_gauc = 0.0
        for parser in lparser_list:
            if parser.has_test:
                max_gauc = max([max(parser.test_gauc_arr), max_gauc])
                self.plot_single(parser, axis, draw_type='Test GAUC', loc='lower right')

        if max_gauc > 0.0:
            max_gauc = math.ceil(max_gauc * 100) / 100
            axis.set_yticks(np.linspace(max_gauc - 0.02, max_gauc, 21), minor=True)
            axis.grid(which='minor', alpha=1.0)

        plt.savefig(filename, dpi=300, bbox_inches='tight')

if __name__ == '__main__':
    class CParser(object):
        """Summary

        Attributes:
            train_loss_avg_window (int): Description
        """
        def __init__(self):
            """Summary
            """
            self.train_loss_avg_window = 1000

    lparser1 = LogParser(CParser())
    lparser1.parselog("/Users/chengru/Desktop/log/draw.py.log", "Draw")

    lparser2 = LogParser(CParser())
    lparser2.parselog("/Users/chengru/Desktop/log/draw2.py.log", "Draw2")

    phandler = PlotHandler(None)
    phandler.draw([lparser1, lparser2], 'custom.png')
