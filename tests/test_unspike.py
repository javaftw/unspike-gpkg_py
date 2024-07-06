import unittest
import sys
import os
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unspike import calculate_angle, filter_polygon, filter_vertices

class TestUnspikingFunctions(unittest.TestCase):

    def poly_2d(self):
        return Polygon([(0, 0, 0), (0, 1, 0), (0.5, 1, 0), (0.6, 10, 0), (0.7, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])
        
        
    def poly_3d(self):
        return Polygon([(0, 0, 0), (0, 1, 0), (0.5, 1, 0), (0.6, 1, 10), (0.7, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])
        
    def poly_3d_nospike(self):
        return Polygon([(0, 0, 0), (0, 1, 0), (0.5, 1, 0), (0.6, 1, 0), (0.7, 1, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0)])

    def test_calculate_angle(self):
        p0 = (0, 0, 0)
        p1 = (1, 1, 1)
        p2 = (1, 0, 0)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 35.26, places=2)

        # Test with collinear points
        p0 = (0, 0, 0)
        p1 = (1, 1, 1)
        p2 = (2, 2, 2)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 180, places=5)

        # Test with very close points
        p0 = (0, 0, 0)
        p1 = (1e-11, 1e-11, 1e-11)
        p2 = (2e-11, 0, 0)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 180, places=5)

        # Test with right angle in 3D
        p0 = (0, 0, 0)
        p1 = (0, 1, 1)
        p2 = (1, 1, 1)
        angle = calculate_angle(p0, p1, p2)
        self.assertAlmostEqual(angle, 90, places=5)

    def test_filter_polygon(self):
        # square with a spike in 2d
        poly = self.poly_2d()
        filtered_poly, spikes_removed = filter_polygon(poly, "dummy_2d_id", 15, False)

        self.assertEqual(spikes_removed, 1)
        self.assertEqual(len(filtered_poly.exterior.coords), 7)
        self.assertTrue(filtered_poly.is_valid)
        
        # square with a spike in 3d
        poly = self.poly_3d()
        filtered_poly, spikes_removed = filter_polygon(poly, "dummy_3d_id", 15, False)

        self.assertEqual(spikes_removed, 1)
        self.assertEqual(len(filtered_poly.exterior.coords), 7)
        self.assertTrue(filtered_poly.is_valid)

        # Test with a polygon that shouldn't be changed
        poly_nochg = self.poly_3d_nospike()
        filtered_poly_nochg, spikes_removed = filter_polygon(poly_nochg, "dummy_id", 5, True)

        self.assertEqual(spikes_removed, 0)
        self.assertEqual(len(filtered_poly_nochg.exterior.coords), 8)
        self.assertTrue(filtered_poly_nochg.equals(poly_nochg))

    def test_filter_vertices(self):
        # Test with a MultiPolygon in 3D
        poly1 = self.poly_2d()
        poly2 = Polygon([(2, 2, 0), (2, 3, 0), (3, 3, 0), (3, 2, 0), (2, 2, 0)])
        multi_poly = MultiPolygon([poly1, poly2])

        filtered_multi_poly, total_spikes_removed = filter_vertices(multi_poly, "dymmy_filter_id", 15, False)

        self.assertEqual(total_spikes_removed, 1)
        self.assertIsInstance(filtered_multi_poly, MultiPolygon)
        self.assertEqual(len(filtered_multi_poly.geoms), 2)
        self.assertEqual(len(filtered_multi_poly.geoms[0].exterior.coords), 7) 
        self.assertEqual(len(filtered_multi_poly.geoms[1].exterior.coords), 5) 

        # Test with a single Polygon in 3D
        single_poly = self.poly_3d()
        filtered_single_poly, spikes_removed = filter_vertices(single_poly, "dummy_filter_id", 15, False)

        self.assertEqual(spikes_removed, 1)
        self.assertIsInstance(filtered_single_poly, Polygon)
        self.assertEqual(len(filtered_single_poly.exterior.coords), 7)

    def test_edge_cases(self):

        # Test with very large coordinate values
        large_poly = Polygon([(0, 0, 0), (0, 1e9, 0), (0.5e9, 1e9, 0), (0.6e9, 1e9, 1e9), (0.7e9, 1e9, 0), (1e9, 1e9, 0), (1e9, 0, 0), (0, 0, 0)])
        filtered_large_poly, spikes_removed = filter_vertices(large_poly, "edge_test_id", 25, False)

        self.assertEqual(spikes_removed, 1)
        self.assertTrue(filtered_large_poly.is_valid)


if __name__ == '__main__':
    unittest.main()