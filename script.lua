local SERVER_URL = "ws://localhost:8765"

local player = game:GetService("Players").LocalPlayer
local HttpService = game:GetService("HttpService")

repeat wait() until player.Character
local Event = player.Character:WaitForChild("PaintingTool", 10).RF

if not Event then
    warn("PaintingTool not found!")
    return
end

print("BABFT Block Art Client")

-- Build 2D grid from blocks
local function getGrid()
    local folder = workspace.Blocks:FindFirstChild(player.Name)
    if not folder then return {} end
    
    local blocks = {}
    for _, b in pairs(folder:GetChildren()) do
        if b.Name == "PlasticBlock" then
            local p = b:GetPivot().Position
            table.insert(blocks, {block = b, y = p.Y, z = p.Z})
        end
    end
    
    if #blocks == 0 then return {} end
    
    -- Sort top-to-bottom, left-to-right
    table.sort(blocks, function(a, b)
        if math.abs(a.y - b.y) > 1 then return a.y > b.y end
        return a.z < b.z
    end)
    
    -- Build rows
    local grid = {}
    local row = {}
    local lastY = blocks[1].y
    
    for _, b in ipairs(blocks) do
        if math.abs(b.y - lastY) > 1 then
            table.insert(grid, row)
            row = {}
            lastY = b.y
        end
        table.insert(row, b.block)
    end
    if #row > 0 then table.insert(grid, row) end
    
    print("Grid: " .. #grid .. "x" .. #grid[1])
    return grid
end

-- Paint changed blocks
local function paint(changes, grid)
    local data = {}
    for _, c in ipairs(changes) do
        local row, col = c.y + 1, c.x + 1
        if grid[row] and grid[row][col] then
            table.insert(data, {grid[row][col], Color3.new(c.r, c.g, c.b)})
        end
    end
    if #data > 0 then Event:InvokeServer(data) end
    return #data
end

-- Main
local function main()
    print("Connecting...")
    local ws = WebSocket.connect(SERVER_URL)
    print("Connected!")
    
    local grid = getGrid()
    if #grid == 0 then ws:Close() return end
    
    local running = true
    local frames = 0
    
    ws.OnMessage:Connect(function(msg)
        local d = HttpService:JSONDecode(msg)
        
        if d.type == "config" then
            print("Mode: " .. d.mode .. " | Size: " .. d.width .. "x" .. d.height)
        elseif d.type == "frame" then
            paint(d.changes, grid)
            frames = frames + 1
            if frames % 30 == 0 then print("Frame " .. frames) end
        elseif d.type == "end" then
            print("Done! " .. frames .. " frames")
            running = false
        elseif d.type == "error" then
            warn(d.error)
            running = false
        end
    end)
    
    ws.OnClose:Connect(function()
        running = false
    end)
    
    while running do wait(1) end
    ws:Close()
end

main()