[
graph TD
    A[Start] --> B[Parse Command Line Arguments]
    B --> C[Open Input GeoPackage]
    C --> D[Create Output GeoPackage]
    D --> E[Process Features]
    E --> F{Is Feature Polygon?}
    F -->|Yes| G[Filter Polygon]
    F -->|No| H[Filter MultiPolygon]
    G --> I[Remove Spikes]
    H --> I
    I --> J{Is Filtered Geometry Valid?}
    J -->|Yes| K[Write to Output]
    J -->|No| L[Skip Feature]
    K --> M{More Features?}
    L --> M
    M -->|Yes| E
    M -->|No| N[Close GeoPackages]
    N --> O[Print Summary]
    O --> P[End]

    subgraph filter_polygon[Filter Polygon]
        G1[Get Coordinates] --> G2[Calculate Angles]
        G2 --> G3[Remove Vertices Below Threshold]
        G3 --> G4[Handle Start/End Point]
        G4 --> G5[Create New Polygon]
        G5 --> G6[Validate Polygon]
    end

    subgraph calculate_angle[Calculate Angle]
        CA1[Convert Points to Vectors] --> CA2[Calculate Dot Product]
        CA2 --> CA3[Calculate Vector Norms]
        CA3 --> CA4[Apply Dot Product Formula]
        CA4 --> CA5[Convert to Degrees]
    end
]
