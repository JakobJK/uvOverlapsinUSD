from pxr import Usd, UsdGeom

class DetectOverlappingUVs():
    def __init__(self, size, usdPath, loadPayloads = False):
        self.size = size
        self.stage = Usd.Stage.Open(usdPath)
        self.buffers = {}
        self.overlaps = set()
        
        if not self.stage:
            print("Failed to open stage")
            return
        
        if loadPayloads:
            self.stage.LoadPayloads()

    def _dumbestFanAlgorithmEver(self, UVs):
        output = []
        first = UVs[0]
        for i in range(1, len(UVs)- 1):
            output.append([first, UVs[i], UVs[i+1]])
        return output

    def _createBuffer(self):
        return [ None ] * self.size * self.size
    
    def _getUDIMfromUV(self, UV):
        u, v = UV
        if u < 0 or u > 10 or v < 0:
            return -1
        
        return 1001 + int(v) * 10 + int(u)

    def clear(self):
        self.buffers = {}
        self.overlaps = set()

    def _fillBuffer(self, y, xStart, xEnd, buffer, faceIndex, primName):
        for x in range(int(xStart), int(xEnd + 1)):
            position = buffer[x + y * self.size]
            if position and position[0] != primName:
                self.overlaps.add((primName, faceIndex))
                self.overlaps.add((position[0], position[1]))
            else:
                buffer[x + y * self.size] = (primName, faceIndex)
    
    def _paintTriangle(self, UVs, buffer, faceIndex, primName):
        a, b, c = UVs
        invTSlope1, invTSlope2 = 0.0, 0.0
        invBSlope1, invBSlope2 = 0.0, 0.0
        
        if (a[1] != b[1]):
            invTSlope1 = (b[0] - a[0]) / abs(b[1] - a[1])
            
        if (a[1] != c[1]):
            invTSlope2 = float(c[0] - a[0]) / abs(c[1] - a[1])
            invBSlope2 = invTSlope2
        
        if (c[1] != b[1]):
            invBSlope1 = (c[0] - b[0]) / abs(c[1] - b[1])
            
        if a[1] != b[1]:
            for y in range(int(a[1] * self.size), int(b[1] * self.size)):
                xStart = (b[0] * self.size) + (y - (b[1] * self.size)) * invTSlope1
                xEnd = (a[0] * self.size) + (y - (a[1] * self.size)) * invTSlope2
                if xEnd < xStart: xEnd, xStart = xStart, xEnd
                self._fillBuffer(y, xStart, xEnd, buffer, faceIndex, primName)
                
        if b[1] != c[1]:
            for y in range(int(b[1] * self.size), int(c[1] * self.size)):
                xStart = b[0] * self.size + (y - b[1] * self.size) * invBSlope1
                xEnd = a[0] * self.size + (y - a[1] * self.size) * invBSlope2
                if xEnd < xStart: xEnd, xStart = xStart, xEnd
                self._fillBuffer(y, xStart, xEnd, buffer, faceIndex, primName)


    def _traverseUVs(self, prim):
        mesh = UsdGeom.Mesh(prim)
        primName = prim.GetPath()
        uvPrimvar = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
        uvVals = uvPrimvar.Get(Usd.TimeCode.Default())

        if uvPrimvar:
            faceVertCount = mesh.GetFaceVertexCountsAttr().Get()
            UVidx = uvPrimvar.GetIndices(Usd.TimeCode.Default())
            index = 0
            for idx, count in enumerate(faceVertCount):
                faceUVs = []
                for _ in range(count):
                    faceUVs.append(uvVals[UVidx[index]])
                    index += 1
                udim = self._getUDIMfromUV(faceUVs[0]) 
                normalizedFaceUVs = [(uv[0] - int(uv[0]), uv[1] - int(uv[1])) for uv in faceUVs]

                if udim not in self.buffers:
                    self.buffers[udim] = self._createBuffer()
                triangles = self._dumbestFanAlgorithmEver(normalizedFaceUVs)
                for triangle in triangles:
                    t = sorted(triangle,key=lambda x: x[1])
                    self._paintTriangle(t, self.buffers[udim], idx, primName)
        
    def findOverlaps(self):
        self.clear()
        meshPrims = [x for x in self.stage.Traverse() if x.IsA(UsdGeom.Mesh)]
        for prim in meshPrims:
            self._traverseUVs(prim)

        for key in self.buffers:
            print(f"UDIM {key} checked!")
        for buffer in self.buffers.values():
            s = ""
            for i in range(len(buffer)):
                if i % self.size == 0:
                    s += "\n"
                if buffer[i]:
                    s += "X"
                else:
                    s += "."
            print(s)

if __name__ == "__main__":
    # Path to USD file:
    usdPath = "D:/repos/mcUSD/Example.usd"
    detector = DetectOverlappingUVs(256, usdPath)
    detector.findOverlaps()
