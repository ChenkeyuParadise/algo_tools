from draw_torch import LogParser, PlotHandler


class CParser(object):
    """Summary

    Attributes:
        train_loss_avg_window (int): Description
    """
    def __init__(self):
        """Summary
        """
        self.train_loss_avg_window = 5000



#lparser9 = LogParser(CParser())
#lparser9.parselog("/home/keyu.cky/workspace/xdl_10_18407_1500518354/log/py.log", "Baseline")

#lparser10 = LogParser(CParser())
#lparser10.parselog("/home/keyu.cky/workspace/xdl_21_529_1500470080/log/py.log", "Baseline_&ad_id_image")


#lparser11 = LogParser(CParser())
#lparser11.parselog("/home/keyu.cky/workspace/xdl_18_27091_1500891896/log/py.log", "Baseline_&ad_doc2vec_id_image")

lparser1 = LogParser(CParser())
lparser1.parselog("log.deep.txt", "deep net")

lparser2 = LogParser(CParser())
lparser2.parselog("log.wide.txt", "wide net")

lparser3 = LogParser(CParser())
lparser3.parselog("log.deep.wide.txt", "deep&wide net")
#lparser3 = LogParser(CParser())
lparser4 = LogParser(CParser())
lparser4.parselog("log.deep.fm.txt", "deep fm net")
#lparser3.parselog("log.deep.wide.txt", "wide net")
#lparser12 = LogParser(CParser())
#lparser12.parselog("/home/keyu.cky/workspace/xdl_23_1492_1503589492/log/py.log", "ad_user_paper_perfect_st2")


phandler = PlotHandler(None)
phandler.draw([lparser1, lparser2, lparser3, lparser4], 'paper_graph_banner_paper.png')
    
    

    
    
