#!/usr/bin/python

import xapian

def auto_enquote(x):
    if x.find(" ")==-1:
        return x
    else:
        return '"' + x + '"'

if __name__ == "__main__":
    import sys
    query = " ".join(map(auto_enquote, sys.argv[1:]))
    qp = xapian.QueryParser()
    qp.add_prefix("title", "S")
    qp.add_prefix("speaker", "XS")
    qp.set_stemmer(xapian.Stem("en"))
    qp.set_stemming_strategy(xapian.QueryParser.STEM_ALL)
    qp.set_default_op(xapian.Query.OP_OR)
    db = xapian.Database("shakespeare")
    qp.set_database(db)
    q = qp.parse_query(query)
    print q.get_description()

    enq = xapian.Enquire(db)
    enq.set_query(q)
    mset = enq.get_mset(0, 10)
    for match in mset:
        data = match[4].get_data()
        def r(x, y):
            x[y.split('=')[0]]=y.split('=')[1]
            return x
        f = reduce(r, data.split('\n'), {})
        print "%2.2i (%3.3i%%) %s, %s, %s" % (match[2]+1,
                                              match[3],
                                              f['play'],
                                              f['act'],
                                              f['scene'])
