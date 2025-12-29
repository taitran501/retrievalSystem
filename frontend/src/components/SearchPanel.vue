<template>
  <div class="bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 min-h-screen flex">
    <!-- Left Sidebar - Search Panel (Resizable, Sticky) -->
    <div 
      class="bg-gray-800 shadow-2xl flex flex-col border-r border-gray-700 relative sticky top-0 self-start"
      :style="{ width: `${sidebarWidth}px`, minWidth: '200px', maxWidth: '500px', maxHeight: '100vh', overflowY: 'auto' }"
    >
      <!-- Resize Handle -->
      <div 
        class="absolute top-0 right-0 w-1 h-full cursor-col-resize hover:bg-blue-500 transition-colors z-50"
        @mousedown="startResize"
      ></div>
      <!-- Header in Sidebar -->
      <div class="p-4 border-b border-gray-700 bg-gray-900/50">
        <div class="flex justify-between items-center mb-2">
          <h1 class="text-lg font-bold text-white tracking-wide">Search Panel</h1>
          <button 
            @click="showLoginModal = true"
            :class="dresConnected ? 'bg-green-600 hover:bg-green-700' : 'bg-gray-600 hover:bg-gray-700'"
            class="px-3 py-1 text-white rounded text-xs font-medium"
          >
            {{ dresConnected ? '✓' : 'DRES' }}
          </button>
        </div>
        
        <div class="flex flex-wrap gap-2 items-center text-xs">
          <div class="text-gray-400 font-medium">{{ results.length }} results</div>
          
          <!-- View Mode Toggle -->
          <button 
            @click="toggleViewMode"
            class="px-2 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-xs font-semibold transition-colors"
            :title="viewMode === 'grouped' ? 'Switch to flat view' : 'Switch to grouped view'"
          >
            {{ viewMode === 'grouped' ? '📊 Grouped' : '� Flat' }}
          </button>
          
          <!-- Top-K Filter -->
          <div class="flex items-center gap-1 flex-wrap">
            <label class="text-gray-400 font-medium whitespace-nowrap">Top-K:</label>
            
            <!-- Preset Buttons -->
            <div class="flex gap-1">
              <button 
                v-for="preset in [50, 100, 200, 500]" 
                :key="preset"
                @click="topK = preset"
                :class="topK === preset ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
                class="px-2 py-1 rounded text-xs font-semibold transition-colors"
              >
                {{ preset }}
              </button>
            </div>
            
            <!-- Custom Input -->
            <input 
              v-model.number="topK" 
              type="number" 
              min="10" 
              max="1000" 
              class="w-14 bg-gray-700 text-white border border-gray-600 rounded px-1.5 py-1 text-xs focus:ring-1 focus:ring-blue-500 outline-none"
            />
          </div>
        </div>
      </div>

      <!-- Search Panel Content -->
      <div class="p-4 flex-1 space-y-3">
        
        <!-- Tabs -->
        <div class="grid grid-cols-2 gap-2">
          <button 
            @click="mode = 'standard'"
            :class="mode === 'standard' ? 'bg-blue-600 text-white shadow-lg' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
            class="px-3 py-2.5 rounded font-semibold transition-all text-sm"
          >
            Standard
          </button>
          <button 
            @click="mode = 'temporal'"
            :class="mode === 'temporal' ? 'bg-indigo-600 text-white shadow-lg' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'"
            class="px-3 py-2.5 rounded font-semibold transition-all text-sm"
          >
            Temporal
          </button>
          <!-- OCR button removed -->
        </div>

      <!-- Standard Text Input -->
      <div v-if="mode === 'standard'">
        <textarea 
          v-model="query" 
          @keydown.enter.prevent="handleSearch"
          class="w-full bg-gray-700 text-white border border-gray-600 rounded-lg p-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none text-sm leading-relaxed"
          :placeholder="getPlaceholder()"
          rows="10"
        ></textarea>
      </div>
        
      <!-- Temporal dynamic inputs -->
      <div v-if="mode === 'temporal'" class="space-y-2">
        <div v-for="(tq, index) in temporalQueries" :key="index" class="flex gap-2">
          <textarea 
            v-model="temporalQueries[index]" 
            @keydown.enter.prevent="handleSearch"
            class="flex-1 bg-gray-700 text-white border border-gray-600 rounded-lg p-3 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm leading-relaxed"
            :placeholder="`Scene ${index + 1}...`"
            rows="6"
          ></textarea>
          <button 
            v-if="temporalQueries.length > 2"
            @click="removeTemporalQuery(index)"
            class="px-3 bg-red-600 hover:bg-red-700 text-white rounded text-sm font-semibold"
            title="Remove this query"
          >
            ✕
          </button>
        </div>
        <button 
          @click="addTemporalQuery"
          class="w-full py-2 bg-indigo-700 hover:bg-indigo-800 text-white rounded-lg text-sm font-semibold flex items-center justify-center gap-1 transition-all"
        >
          <span class="text-lg">+</span> Add Scene
        </button>
      </div>

      <!-- OCR Input -->
      <!-- OCR Input removed -->

      <!-- Search Button -->
      <button 
        @click="handleSearch"
        :disabled="loading || !canSearch()"
        class="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-bold py-3 rounded-lg transition-all text-sm shadow-lg hover:shadow-xl"
      >
        {{ loading ? 'Searching...' : '🔍 Search' }}
      </button>

      <!-- Submit Button -->
      <button 
        v-if="selectedFrames.length > 0"
        @click="showSubmitModal = true"
        class="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 rounded-lg transition-all text-sm shadow-lg hover:shadow-xl flex items-center justify-center gap-2 mt-2"
      >
        <span>📤 Submit</span>
        <span class="bg-green-800 px-2 py-0.5 rounded-full text-xs font-semibold">{{ selectedFrames.length }}</span>
      </button>

      <!-- Search History Footer -->
      <div class="mt-auto pt-4 border-t border-gray-700">
        <div class="flex justify-between items-center mb-2">
          <h3 class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Search History</h3>
          <button 
            v-if="searchHistory.length > 0"
            @click="clearHistory"
            class="text-xs text-red-400 hover:text-red-300 transition-colors"
          >
            Clear
          </button>
        </div>
        
        <div v-if="searchHistory.length === 0" class="text-xs text-gray-600 italic text-center py-2">
          No history
        </div>
        
        <div class="space-y-1.5 overflow-hidden">
          <div 
            v-for="(item, idx) in searchHistory.slice(0, 5)" 
            :key="idx"
            class="group flex items-start gap-1 bg-gray-900/40 hover:bg-gray-700 rounded p-2 transition-all border border-transparent hover:border-gray-600"
          >
            <div 
              @click="applyHistoryItem(item)"
              class="flex-1 cursor-pointer"
            >
              <div class="text-xs text-gray-300 line-clamp-2 leading-relaxed group-hover:text-white">
                {{ item }}
              </div>
            </div>
            
            <button 
              @click.stop="deleteHistoryItem(idx)"
              class="text-gray-600 hover:text-red-400 p-0.5 opacity-0 group-hover:opacity-100 transition-all font-bold"
              title="Delete from history"
            >
              &times;
            </button>
          </div>
        </div>
        
        <!-- See All Trigger (optional, if list is long) -->
        <button 
           v-if="searchHistory.length > 5"
           @click="showHistoryModal = true"
           class="w-full text-xs text-center text-gray-500 hover:text-gray-300 mt-2 py-1"
        >
          View all {{ searchHistory.length }}
        </button>
      </div>

    </div>  <!-- Close Search Panel Content -->
    </div>  <!-- Close Sidebar -->

    <!-- Main Content Area - Results -->
    <div class="flex-1 p-4">
      
      <!-- Grouped View Mode -->
      <div v-if="viewMode === 'grouped' && groupedResults.length > 0" class="space-y-3">
        <!-- Video Group -->
        <div 
          v-for="(group, groupIdx) in groupedResults" 
          :key="group.video"
          class="bg-gray-800 rounded-lg overflow-hidden shadow-lg transition-all"
          :style="{ borderLeft: `4px solid ${group.color}` }"
        >
          <!-- Video Header -->
          <div 
            @click="toggleVideoExpand(group.video)"
            class="flex items-center justify-between p-3 bg-gray-900/50 cursor-pointer hover:bg-gray-900/70 transition-colors"
          >
            <div class="flex items-center gap-2.5">
              <!-- Color Indicator -->
              <div 
                class="w-2.5 h-2.5 rounded-full shadow-lg" 
                :style="{ backgroundColor: group.color }"
              ></div>
              
              <!-- Video Name -->
              <div class="text-white font-bold text-sm">{{ group.video }}</div>
              
              <!-- Frame Count Badge -->
              <div class="bg-gray-700 text-gray-300 px-2 py-0.5 rounded-full text-xs font-semibold">
                {{ group.frames.length }} frames
              </div>
              
              <!-- Top Score -->
              <div class="text-gray-400 text-xs font-mono">
                Top: {{ group.topScore.toFixed(3) }}
              </div>
            </div>
            
            <!-- Expand/Collapse Icon -->
            <div class="text-gray-400 transition-transform" :class="{ 'rotate-90': isVideoExpanded(group.video) }">
              <span class="text-lg">▶</span>
            </div>
          </div>
          
          <!-- Frames Grid -->
          <div class="p-3 bg-gray-800/50">
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
              <!-- Show first 6 or all if expanded -->
              <div 
                v-for="(item, idx) in (isVideoExpanded(group.video) ? group.frames : group.frames.slice(0, 6))" 
                :key="idx"
                class="relative group cursor-pointer rounded overflow-hidden transition-all hover:scale-105 border-2"
                :class="`hover:ring-2 border-${group.color.replace('#', '')}`"
                :style="{ '--hover-ring-color': group.color }"
                @click="openPreview(item)"
              >
                <!-- Selection Checkbox -->
                <div class="absolute top-1 left-1 z-10">
                  <input 
                    type="checkbox" 
                    :checked="isSelected(item)"
                    @click.stop="toggleSelection(item)"
                    class="w-3.5 h-3.5 cursor-pointer accent-blue-500"
                  />
                </div>
                
                <!-- Global Rank Badge -->
                <div class="absolute top-1 right-1 z-10 bg-black/80 text-white px-1.5 py-0.5 rounded text-xs font-bold">
                  #{{ item.globalIdx + 1 }}
                </div>
                
                <!-- Thumbnail -->
                <img 
                  :src="`/thumbnails/${item.entity.thumbnail_path || item.entity.keyframe_path}`" 
                  :alt="`${group.video} - ${item.entity.frame_id}`"
                  class="w-full aspect-video object-cover"
                  @error="$event.target.src=`/keyframes/${item.entity.keyframe_path}`"
                />
                
                <!-- Minimal overlay on hover -->
                <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 flex items-center justify-center transition-all">
                  <div class="opacity-0 group-hover:opacity-100 text-white text-2xl">▶</div>
                </div>
                
                <!-- Score badge -->
                <div class="absolute bottom-1 right-1 z-10 bg-black/80 text-yellow-400 px-1.5 py-0.5 rounded text-xs font-bold">
                  {{ item.distance.toFixed(2) }}
                </div>
              </div>
            </div>
            
            <!-- "Show All" Button -->
            <div v-if="!isVideoExpanded(group.video) && group.frames.length > 6" class="mt-2.5">
              <button 
                @click.stop="toggleVideoExpand(group.video)"
                class="w-full py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2"
              >
                <span>Show all {{ group.frames.length }} frames</span>
                <span class="text-xs">▼</span>
              </button>
            </div>
            
            <!-- "Show Less" Button -->
            <div v-else-if="isVideoExpanded(group.video) && group.frames.length > 6" class="mt-2.5">
              <button 
                @click.stop="toggleVideoExpand(group.video)"
                class="w-full py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm font-semibold transition-all flex items-center justify-center gap-2"
              >
                <span>Show less</span>
                <span class="text-xs">▲</span>
              </button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Flat View Mode (Original Grid) -->
      <div v-else-if="viewMode === 'flat' && results.length > 0">
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-2">
          <div 
            v-for="(item, idx) in results" 
            :key="idx" 
            class="bg-gray-800 rounded overflow-hidden hover:ring-2 hover:ring-blue-500 transition-all cursor-pointer relative group"
            @click="openPreview(item)"
          >
            <!-- Selection Checkbox -->
            <div class="absolute top-1 left-1 z-10">
              <input 
                type="checkbox" 
                :checked="isSelected(item)"
                @click.stop="toggleSelection(item)"
                class="w-4 h-4 cursor-pointer"
              />
            </div>
            
            <!-- Rank Badge -->
            <div class="absolute top-1 right-1 z-10 bg-black/70 text-white px-1 rounded text-xs font-bold">
              {{ idx + 1 }}
            </div>
            
            <img 
              :src="`/thumbnails/${item.entity.thumbnail_path || item.entity.keyframe_path}`" 
              :alt="item.entity.video"
              class="w-full aspect-video object-cover transition-opacity duration-300"
              @error="$event.target.src=`/keyframes/${item.entity.keyframe_path}`"
            />
            
            <!-- Play Overlay -->
            <div class="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-40 flex items-center justify-center transition-all">
              <div class="opacity-0 group-hover:opacity-100 text-white text-2xl">▶</div>
            </div>
            
            <div class="p-1 text-xs">
              <div class="text-white truncate font-semibold">{{ item.entity.video }}</div>
              <div class="text-gray-400">{{ item.entity.time }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Empty State -->
      <div v-else-if="!loading && results.length === 0" class="flex flex-col items-center justify-center py-20 text-gray-400">
        <div class="text-6xl mb-4">🔍</div>
        <div class="text-xl font-semibold mb-2">No results yet</div>
        <div class="text-sm">Start searching to see results</div>
      </div>

      <!-- Error Message -->
      <div v-if="error" class="mt-4">
        <div class="bg-red-900 text-white p-4 rounded-lg shadow-lg max-w-2xl">
          ⚠️ {{ error }}
        </div>
      </div>
      
    </div>
  </div>

  <!-- Video Preview Modal -->
  <div 
    v-if="previewFrame" 
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    @click="closePreview"
  >
      <div class="bg-gray-800 rounded-lg max-w-5xl w-full p-3 max-h-[90vh] overflow-y-auto" @click.stop>
        <div class="flex justify-between items-center mb-2">
          <div class="text-white font-semibold text-sm">{{ previewFrame.entity.video }} - {{ previewFrame.entity.time }}</div>
          <button @click="closePreview" class="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        
        <div class="grid grid-cols-3 gap-3 mb-2">
          <!-- Neighbor Frames (Left) -->
          <div>
            <div class="text-gray-400 text-sm font-semibold mb-2">Neighbor Frames</div>
            <div class="grid grid-cols-2 gap-2">
              <div 
                v-for="neighbor in neighborFrames" 
                :key="neighbor.path"
                class="relative group cursor-pointer hover:scale-105 transition-transform"
                @click="openPreview(neighbor.frame)"
              >
                <img 
                  :src="`/thumbnails/${neighbor.frame.entity.thumbnail_path || neighbor.path}`" 
                  class="w-full h-32 object-cover rounded border-2 transition-opacity duration-300"
                  :class="neighbor.offset < 0 ? 'border-blue-500' : 'border-green-500'"
                  @error="$event.target.src=`/keyframes/${neighbor.path}`"
                />
                <div class="absolute top-1.5 right-1.5 bg-black/80 text-white text-xs font-bold px-1.5 py-0.5 rounded">
                  {{ neighbor.offset > 0 ? '+' : '' }}{{ neighbor.offset }}
                </div>
              </div>
            </div>
          </div>
          
          <!-- Video Player (Center/Right) -->
          <div class="col-span-2">
            <div class="bg-black rounded overflow-hidden mb-1">
              <video 
                ref="videoPlayer"
                class="w-full"
                controls
                autoplay
                :poster="`/keyframes/${previewFrame.entity.keyframe_path}`"
                @loadedmetadata="seekToFrameTime"
              >
                <source :src="getVideoPath(previewFrame)" type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>
            
            <!-- Video Controls: Forward/Backward -->
            <div class="flex gap-2 mb-1">
              <button 
                @click="skipBackward"
                class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-1 rounded text-xs flex items-center justify-center gap-1"
              >
                <span>◀</span> -2s
              </button>
              <button 
                @click="skipForward"
                class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-1 rounded text-xs flex items-center justify-center gap-1"
              >
                +2s <span>▶</span>
              </button>
            </div>
            
              <div class="flex gap-2 text-xs text-gray-400 mb-1">
                <span>Frame: {{ previewFrame.entity.frame_id }}</span>
                <span>•</span>
                <span>Time: {{ (previewFrame.entity.time_seconds * 1000).toFixed(0) }}ms</span>
                <span>•</span>
                <span>Score: {{ previewFrame.distance.toFixed(4) }}</span>
              </div>
            
            <!-- KIS Segment Adjustment Controls -->
            <div v-if="previewFrame.entity.kis_segment" class="mb-2 p-2 bg-blue-900/30 border border-blue-500 rounded">
              <div class="flex justify-between items-center mb-1">
                <div class="font-semibold text-blue-300 text-sm">📍 KIS Submission Segment</div>
                <div class="text-blue-400 text-xs font-mono">
                  {{ formatDuration(kisAdjustment.duration) }}
                </div>
              </div>
              
              <!-- Visual Timeline Preview -->
              <div class="mb-2 bg-gray-900/50 rounded p-1.5">
                <div 
                  ref="timelineContainer"
                  class="relative h-6 bg-gray-800 rounded overflow-visible cursor-pointer"
                  @mousedown="handleTimelineClick"
                >
                  <!-- Original Segment (faded) -->
                  <div 
                    class="absolute h-full bg-blue-500/30 pointer-events-none"
                    :style="{
                      left: '0%',
                      width: '100%'
                    }"
                  ></div>
                  
                  <!-- Adjusted Segment (draggable) -->
                  <div 
                    class="absolute h-full bg-blue-500 border-2 border-blue-300 cursor-move hover:bg-blue-400 transition-colors"
                    :style="{
                      left: kisAdjustment.visualLeft + '%',
                      width: kisAdjustment.visualWidth + '%'
                    }"
                    @mousedown.stop="handleSegmentDragStart"
                  >
                    <!-- Left Resize Handle -->
                    <div 
                      class="absolute left-0 top-0 h-full w-2 bg-blue-300 cursor-ew-resize hover:bg-blue-100 transition-colors"
                      @mousedown.stop="handleLeftEdgeDragStart"
                      title="Drag to adjust start time"
                    ></div>
                    
                    <!-- Duration Label -->
                    <div class="flex items-center justify-center h-full text-white text-xs font-bold pointer-events-none">
                      {{ formatDuration(kisAdjustment.duration) }}
                    </div>
                    
                    <!-- Right Resize Handle -->
                    <div 
                      class="absolute right-0 top-0 h-full w-2 bg-blue-300 cursor-ew-resize hover:bg-blue-100 transition-colors"
                      @mousedown.stop="handleRightEdgeDragStart"
                      title="Drag to adjust end time"
                    ></div>
                  </div>
                  
                  <!-- Frame Marker -->
                  <div 
                    class="absolute h-full w-0.5 bg-yellow-400 pointer-events-none"
                    style="left: 50%"
                  >
                    <div class="absolute -top-1 left-1/2 transform -translate-x-1/2 text-yellow-400 text-xs">▼</div>
                  </div>
                </div>
                
                <div class="flex justify-between text-xs text-gray-400 mt-1">
                  <span>{{ formatTime(kisAdjustment.minTime) }}</span>
                  <span class="text-yellow-400">Frame</span>
                  <span>{{ formatTime(kisAdjustment.maxTime) }}</span>
                </div>
              </div>
              
              <!-- Quick Presets -->
              <div class="mb-3 space-y-2">
                
                <!-- Shift Controls (Move entire window) -->
                <div>
                  <div class="text-[10px] text-gray-400 mb-0.5 uppercase tracking-wider font-semibold">Shift Window (Position)</div>
                  <div class="grid grid-cols-4 gap-1">
                     <button 
                      @click="shiftKisWindow(-3)"
                      class="bg-indigo-700 hover:bg-indigo-600 text-white px-2 py-1.5 rounded text-xs font-semibold flex items-center justify-center gap-1"
                      title="Shift back 3 seconds"
                    >
                      <span class="text-[10px]">◀◀</span> -3s
                    </button>
                    <button 
                      @click="shiftKisWindow(-1)"
                      class="bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-1.5 rounded text-xs font-semibold flex items-center justify-center gap-1"
                      title="Shift back 1 second"
                    >
                      <span class="text-[10px]">◀</span> -1s
                    </button>
                     <button 
                      @click="shiftKisWindow(1)"
                      class="bg-indigo-600 hover:bg-indigo-500 text-white px-2 py-1.5 rounded text-xs font-semibold flex items-center justify-center gap-1"
                      title="Shift forward 1 second"
                    >
                      +1s <span class="text-[10px]">▶</span>
                    </button>
                    <button 
                      @click="shiftKisWindow(3)"
                      class="bg-indigo-700 hover:bg-indigo-600 text-white px-2 py-1.5 rounded text-xs font-semibold flex items-center justify-center gap-1"
                      title="Shift forward 3 seconds"
                    >
                      +3s <span class="text-[10px]">▶▶</span>
                    </button>
                  </div>
                </div>

                <!-- Resize Controls (Expand/Shrink) -->
                <div>
                  <div class="text-[10px] text-gray-400 mb-0.5 uppercase tracking-wider font-semibold">Resize Duration</div>
                  <div class="grid grid-cols-6 gap-0.5">
                    <button 
                      @click="adjustKisWindow(-5)"
                      class="bg-gray-700 hover:bg-gray-600 text-white px-1 py-1 rounded text-xs"
                      title="Shrink by 5s"
                    >
                      -5s
                    </button>
                    <button 
                      @click="adjustKisWindow(-2)"
                      class="bg-gray-700 hover:bg-gray-600 text-white px-1 py-1 rounded text-xs"
                      title="Shrink by 2s"
                    >
                      -2s
                    </button>
                    <button 
                      @click="adjustKisWindow(-1)"
                      class="bg-gray-700 hover:bg-gray-600 text-white px-1 py-1 rounded text-xs"
                      title="Shrink by 1s"
                    >
                      -1s
                    </button>
                    <button 
                      @click="adjustKisWindow(1)"
                      class="bg-gray-600 hover:bg-gray-500 text-white px-1 py-1 rounded text-xs"
                      title="Expand by 1s"
                    >
                      +1s
                    </button>
                    <button 
                      @click="adjustKisWindow(2)"
                      class="bg-gray-600 hover:bg-gray-500 text-white px-1 py-1 rounded text-xs"
                      title="Expand by 2s"
                    >
                      +2s
                    </button>
                    <button 
                      @click="adjustKisWindow(5)"
                      class="bg-gray-600 hover:bg-gray-500 text-white px-1 py-1 rounded text-xs"
                      title="Expand by 5s"
                    >
                      +5s
                    </button>
                  </div>
                </div>
              </div>
              
              <!-- Manual Time Inputs -->
              <div class="grid grid-cols-2 gap-2 mb-1.5">
                <div>
                  <label class="block text-xs text-gray-400 mb-1">Start Time</label>
                  <input 
                    type="number" 
                    v-model.number="kisAdjustment.startSeconds"
                    @input="updateKisSegment"
                    :min="0"
                    :max="kisAdjustment.endSeconds - 1"
                    step="0.1"
                    class="w-full bg-gray-700 text-white border border-gray-600 rounded px-2 py-1 text-xs font-mono"
                    @blur="kisAdjustment.startSeconds = Math.round(kisAdjustment.startSeconds * 10) / 10"
                  />
                  <div class="text-xs text-gray-500 mt-0.5">{{ formatTime(kisAdjustment.startSeconds) }}</div>
                </div>
                
                <div>
                  <label class="block text-xs text-gray-400 mb-1">End Time</label>
                  <input 
                    type="number" 
                    v-model.number="kisAdjustment.endSeconds"
                    @input="updateKisSegment"
                    :min="kisAdjustment.startSeconds + 1"
                    step="0.1"
                    class="w-full bg-gray-700 text-white border border-gray-600 rounded px-2 py-1 text-xs font-mono"
                    @blur="kisAdjustment.endSeconds = Math.round(kisAdjustment.endSeconds * 10) / 10"
                  />
                  <div class="text-xs text-gray-500 mt-0.5">{{ formatTime(kisAdjustment.endSeconds) }}</div>
                </div>
              </div>
              
              <!-- Reset Button -->
              <button 
                @click="resetKisSegment"
                class="w-full bg-gray-700 hover:bg-gray-600 text-white py-1 rounded text-xs font-semibold mb-1.5"
              >
                🔄 Reset to Default (3s Window)
              </button>
              
              <!-- Warning for long segments -->
              <div v-if="kisAdjustment.duration > 20" class="text-yellow-400 text-xs flex items-start gap-1 bg-yellow-900/20 p-2 rounded">
                <span>⚠️</span>
                <span>Segment > 20s may be rejected. Keep it close to the actual event.</span>
              </div>
            </div>
            
            <!-- DRES Submit Section (replaces Select button) -->
            <div class="space-y-2">
              <!-- Task Type & Status -->
              <div class="flex gap-2 items-center">
                <select 
                  v-model="previewSubmitConfig.taskType" 
                  class="flex-1 bg-gray-700 text-white border border-gray-600 rounded px-2 py-1.5 text-xs"
                >
                  <option value="kis">KIS</option>
                  <option value="qa">QA</option>
                </select>
                
                <div class="text-xs px-2" :class="dresConnected ? 'text-green-400' : 'text-gray-500'">
                  {{ dresConnected ? '● DRES' : '○ Offline' }}
                </div>
              </div>
              
              <!-- QA Answer Input (inline) -->
              <input 
                v-if="previewSubmitConfig.taskType === 'qa'" 
                v-model="previewSubmitConfig.answerText" 
                placeholder="Answer (e.g., 5, A, text...)"
                class="w-full bg-gray-700 text-white border border-gray-600 rounded px-3 py-1.5 text-xs"
              />
              
              <!-- Submit Buttons -->
              <div class="grid grid-cols-2 gap-2">
                <button 
                  @click="copySingleFrameJson"
                  class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold transition-all text-sm"
                  title="Copy JSON for manual submission"
                >
                  📋 Copy JSON
                </button>
                <button 
                  @click="submitSingleFrame"
                  :disabled="submitting || !dresSession.sessionId"
                  :class="submitting ? 'bg-gray-600' : 'bg-green-600 hover:bg-green-700'"
                  class="px-4 py-2 text-white rounded font-semibold transition-all text-sm disabled:cursor-not-allowed"
                >
                  {{ submitting ? 'Submitting...' : '🚀 Submit' }}
                </button>
              </div>
              
              <!-- Result Message -->
              <div v-if="previewSubmitResult" :class="previewSubmitResult.success ? 'text-green-400' : 'text-red-400'" class="text-xs text-center">
                {{ previewSubmitResult.message }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  <!-- DRES Login Modal -->
  <div 
    v-if="showLoginModal" 
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    @click="showLoginModal = false"
  >
      <div class="bg-gray-800 rounded-lg max-w-md w-full p-4" @click.stop>
        <h2 class="text-lg font-bold text-white mb-4">DRES Login</h2>
        
        <div class="mb-3">
          <label class="block text-gray-400 mb-1 text-xs">DRES Server URL</label>
          <input 
            v-model="dresBaseUrl" 
            class="w-full bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm font-mono" 
            placeholder="http://192.168.1.100:8080"
          />
          <div class="text-xs text-gray-500 mt-1">Optional: Override server address</div>
        </div>
        
        <div class="mb-3">
          <label class="block text-gray-400 mb-1 text-xs">Username</label>
          <input v-model="dresLogin.username" class="w-full bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm" />
        </div>
        
        <div class="mb-3">
          <label class="block text-gray-400 mb-1 text-xs">Password</label>
          <input v-model="dresLogin.password" type="password" class="w-full bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm" />
        </div>
        
        <div class="flex gap-2">
          <button 
            @click="loginDRES"
            :disabled="loggingIn"
            class="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white py-2 rounded font-semibold text-sm"
          >
            {{ loggingIn ? 'Logging in...' : 'Login' }}
          </button>
          
          <button 
            v-if="dresConnected"
            @click="logoutDRES"
            class="flex-1 bg-red-700 hover:bg-red-600 text-white py-2 rounded font-semibold text-sm"
          >
            Logout
          </button>
          
          <button 
            @click="showLoginModal = false"
            class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded font-semibold text-sm"
          >
            Cancel
          </button>
        </div>
        
        <div v-if="loginError" class="mt-3 text-red-400 text-xs">
          {{ loginError }}
        </div>
      </div>
    </div>

  <!-- DRES Submit Modal -->
  <div 
    v-if="showSubmitModal" 
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    @click="showSubmitModal = false"
  >
      <div class="bg-gray-800 rounded-lg max-w-md w-full p-4" @click.stop>
        <h2 class="text-lg font-bold text-white mb-4">Submit to DRES</h2>
        
        <div class="mb-3">
          <label class="block text-gray-400 mb-1 text-xs">Task Type</label>
          <select v-model="dresConfig.taskType" class="w-full bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm">
            <option value="kis">KIS</option>
            <option value="qa">QA</option>
          </select>
        </div>
        
        <div class="mb-3" v-if="dresConfig.taskType === 'kis'">
          <label class="block text-gray-400 mb-1 text-xs">Default Window (± seconds)</label>
          <div class="flex gap-2 items-center">
            <input 
              type="number" 
              step="0.1" 
              v-model.number="dresConfig.kisWindow" 
              class="flex-1 bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm" 
            />
            <span class="text-xs text-gray-500">Total: {{ (dresConfig.kisWindow * 2).toFixed(1) }}s</span>
          </div>
          <div class="text-[10px] text-gray-500 mt-1">Smaller window = higher precision, recommended for KIS.</div>
        </div>
        
        <div class="mb-3" v-if="dresConfig.taskType === 'qa'">
          <label class="block text-gray-400 mb-1 text-xs">Answer</label>
          <input v-model="dresConfig.answerText" class="w-full bg-gray-700 text-white border border-gray-600 rounded p-2 text-sm" />
        </div>
        
        <div class="mb-3 text-gray-400 text-sm">
          {{ selectedFrames.length }} frame(s)
        </div>
        
        <div class="flex gap-2">
          <button 
            @click="copyDRESJson"
            class="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded font-semibold text-sm"
            title="Copy JSON for manual submission"
          >
            📋 Copy JSON
          </button>
          <button 
            @click="submitToDRES"
            :disabled="submitting"
            class="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white py-2 rounded font-semibold text-sm"
          >
            {{ submitting ? 'Submitting...' : '🚀 Submit' }}
          </button>
          <button 
            @click="showSubmitModal = false"
            class="flex-1 bg-gray-700 hover:bg-gray-600 text-white py-2 rounded font-semibold text-sm"
          >
            Cancel
          </button>
        </div>
        
        <div v-if="submitResult" :class="submitResult.success ? 'text-green-400' : 'text-red-400'" class="mt-3 text-xs">
          {{ submitResult.message }}
        </div>
      </div>
    </div>

  <!-- Search History Modal -->
  <div 
    v-if="showHistoryModal" 
    class="fixed inset-0 bg-black/95 flex items-center justify-center z-50 p-4"
    @click="showHistoryModal = false"
  >
      <div class="bg-gray-800 rounded-lg max-w-lg w-full p-4 max-h-[80vh] flex flex-col" @click.stop>
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-lg font-bold text-white">Search History</h2>
          <button @click="showHistoryModal = false" class="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>
        
        <div class="overflow-y-auto flex-1 space-y-2 pr-2 mb-4 custom-scrollbar">
          <div v-if="searchHistory.length === 0" class="text-gray-500 text-center py-8 italic">
            No history yet
          </div>
          
          <div 
            v-for="(item, idx) in searchHistory" 
            :key="idx"
            class="flex items-start gap-3 bg-gray-700/50 hover:bg-gray-700 rounded p-3 transition-colors group border border-transparent hover:border-gray-600"
          >
            <div 
              @click="applyHistoryItem(item); showHistoryModal = false"
              class="flex-1 cursor-pointer text-sm text-gray-200 hover:text-white"
            >
              {{ item }}
            </div>
            
            <button 
              @click="deleteHistoryItem(idx)"
              class="text-gray-500 hover:text-red-400 p-1 opacity-50 group-hover:opacity-100 transition-opacity"
              title="Remove"
            >
              🗑️
            </button>
          </div>
        </div>
        
        <div class="flex justify-between items-center pt-3 border-t border-gray-700">
          <span class="text-xs text-gray-500">Total: {{ searchHistory.length }} items</span>
          <button 
            @click="clearHistory"
            class="text-red-400 hover:text-red-300 text-sm font-semibold px-3 py-1 bg-red-900/20 hover:bg-red-900/40 rounded transition-colors"
          >
            Clear All History
          </button>
        </div>
      </div>
    </div>

</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const query = ref('');
const temporalQueries = ref(['', '']);  // Array of queries for temporal mode
const ocrQuery = ref('');
const mode = ref('standard');
const loading = ref(false);
const submitting = ref(false);
const loggingIn = ref(false);
const results = ref([]);
const error = ref('');
const selectedFrames = ref([]);
const previewFrame = ref(null);
const neighborFrames = ref([]);
const showSubmitModal = ref(false);
const showLoginModal = ref(false);
const showHistoryModal = ref(false);
const submitResult = ref(null);
const loginError = ref('');
const videoPlayer = ref(null);
const timelineContainer = ref(null);
const topK = ref(100);

const searchHistory = ref([]);
onMounted(() => {
  const saved = localStorage.getItem('searchHistory');
  if (saved) {
    try {
      searchHistory.value = JSON.parse(saved);
    } catch(e) { 
      console.error('Failed to load history', e); 
    }
  }
});

function addToHistory(text) {
  if (!text || !text.trim()) return;
  text = text.trim();
  
  // Remove duplicates
  searchHistory.value = searchHistory.value.filter(item => item !== text);
  
  // Add to top
  searchHistory.value.unshift(text);
  
  // Limit to 100
  if (searchHistory.value.length > 100) {
    searchHistory.value = searchHistory.value.slice(0, 100);
  }
  
  localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value));
}

function deleteHistoryItem(index) {
  searchHistory.value.splice(index, 1);
  localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value));
}

function clearHistory() {
  if(confirm('Clear all search history?')) {
    searchHistory.value = [];
    localStorage.removeItem('searchHistory');
  }
}

function applyHistoryItem(text) {
  if (mode.value === 'temporal') {
    // If likely a temporal query (comma separated), split it?
    // Or just put in first slot?
    // For simplicity, put in first slot or append?
    // User wants "fast copy". Replace first slot is safest.
    if (temporalQueries.value.length > 0) {
        temporalQueries.value[0] = text;
    } else {
        temporalQueries.value.push(text);
    }
  } else {
    query.value = text;
  }
}

// Drag state for timeline
const dragState = ref({
  isDragging: false,
  dragType: null, // 'move', 'resize-left', 'resize-right'
  startX: 0,
  startLeft: 0,
  startWidth: 0
});

// Video grouping state
const expandedVideos = ref(new Set());
const viewMode = ref('grouped'); // 'grouped' or 'flat'

// Sidebar resize state
const sidebarWidth = ref(256); // Start at w-64 (256px)
const isResizing = ref(false);


// KIS Segment Adjustment state
const kisAdjustment = ref({
  startSeconds: 0,
  endSeconds: 6,
  duration: 6,
  originalStart: 0,
  originalEnd: 6,
  frameTime: 3,
  minTime: 0,
  maxTime: 10,
  visualLeft: 0,
  visualWidth: 100
});

// DRES state
const dresConnected = ref(false);
const dresSession = ref({
  sessionId: localStorage.getItem('contestSessionID') || '',
  evaluationId: localStorage.getItem('evaluationID') || '',
  evaluationName: '',
  username: ''
});

const dresLogin = ref({
  username: '',
  password: ''
});

const dresConfig = ref({
  taskType: 'kis',
  answerText: '',
  kisWindow: 2.5 // Default +/- 2.5s (5s total)
});

// Preview modal submit config (separate from bulk submit)
const previewSubmitConfig = ref({
  taskType: 'kis',
  answerText: '',
  kisWindow: 2.5 // Default +/- 2.5s
});
const previewSubmitResult = ref(null);

const dresBaseUrl = ref('http://192.168.20.156:5601');

// Color palette for video groups
const VIDEO_COLORS = [
  '#FCD34D', // yellow
  '#A78BFA', // purple  
  '#34D399', // green
  '#60A5FA', // blue
  '#F87171', // red
  '#FB923C', // orange
  '#F472B6', // pink
  '#2DD4BF', // teal
  '#C084FC', // violet
  '#FBBF24', // amber
  '#22D3EE', // cyan
  '#A3E635', // lime
];

function getVideoColor(video) {
  // Deterministic color assignment based on video name
  const hash = video.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return VIDEO_COLORS[hash % VIDEO_COLORS.length];
}

// Computed property to group results by video
const groupedResults = computed(() => {
  if (results.value.length === 0) return [];
  
  // Group by video
  const groups = {};
  results.value.forEach((result, globalIdx) => {
    const video = result.entity.video;
    if (!groups[video]) {
      groups[video] = {
        video: video,
        frames: [],
        avgScore: 0,
        topScore: 0,
        color: getVideoColor(video)
      };
    }
    groups[video].frames.push({ ...result, globalIdx });
  });
  
  // Calculate statistics
  Object.values(groups).forEach(group => {
    const scores = group.frames.map(f => f.distance || 0);
    group.avgScore = scores.reduce((a, b) => a + b, 0) / scores.length;
    group.topScore = Math.max(...scores);
  });
  
  // Sort groups by top score (descending)
  return Object.values(groups).sort((a, b) => b.topScore - a.topScore);
});

function toggleVideoExpand(video) {
  if (expandedVideos.value.has(video)) {
    expandedVideos.value.delete(video);
  } else {
    expandedVideos.value.add(video);
  }
  // Force reactivity
  expandedVideos.value = new Set(expandedVideos.value);
}

function isVideoExpanded(video) {
  return expandedVideos.value.has(video);
}

function toggleViewMode() {
  viewMode.value = viewMode.value === 'grouped' ? 'flat' : 'grouped';
}

// Sidebar resize handlers
function startResize(e) {
  isResizing.value = true;
  document.addEventListener('mousemove', handleResize);
  document.addEventListener('mouseup', stopResize);
  e.preventDefault();
}

function handleResize(e) {
  if (!isResizing.value) return;
  const newWidth = e.clientX;
  sidebarWidth.value = Math.max(200, Math.min(500, newWidth));
}

function stopResize() {
  isResizing.value = false;
  document.removeEventListener('mousemove', handleResize);
  document.removeEventListener('mouseup', stopResize);
}

function getConfidenceColor(confidence) {
  if (confidence >= 80) return 'bg-green-500/90 text-white';
  if (confidence >= 60) return 'bg-yellow-500/90 text-black';
  if (confidence >= 40) return 'bg-orange-500/90 text-white';
  return 'bg-red-500/90 text-white';
}

function getConfidenceCardColor(confidence) {
  if (confidence >= 80) return 'bg-green-900/30 border border-green-500 text-green-100';
  if (confidence >= 60) return 'bg-yellow-900/30 border border-yellow-500 text-yellow-100';
  if (confidence >= 40) return 'bg-orange-900/30 border border-orange-500 text-orange-100';
  return 'bg-red-900/30 border border-red-500 text-red-100';
}

function getConfidenceTooltip(item) {
  if (!item.confidence_reasons) return `Confidence: ${Math.round(item.submission_confidence)}%`;
  return item.confidence_reasons.slice(0, 3).join('\n');
}

function getTopConfidenceFrame() {
  if (results.value.length === 0) return null;
  const topFrame = results.value.reduce((best, curr) => {
    const currConf = curr.submission_confidence || 0;
    const bestConf = best.submission_confidence || 0;
    return currConf > bestConf ? curr : best;
  }, results.value[0]);
  return (topFrame.submission_confidence || 0) >= 80 ? topFrame : null;
}

async function quickSubmitTopFrame() {
  const topFrame = getTopConfidenceFrame();
  if (!topFrame) return;
  
  selectedFrames.value = [topFrame];
  showSubmitModal.value = true;
  
  // Auto-submit after 1 second if still in modal
  setTimeout(() => {
    if (showSubmitModal.value && selectedFrames.value.length === 1) {
      submitToDRES();
    }
  }, 1000);
}

function formatTime(seconds) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDuration(seconds) {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const mins = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(0);
  return `${mins}m ${secs}s`;
}

function initKisAdjustment(frame) {
  if (!frame || !frame.entity.kis_segment) return;
  
  const segment = frame.entity.kis_segment;
  const frameTime = frame.entity.time_seconds || 0;
  
  // Set up adjustment state
  kisAdjustment.value = {
    startSeconds: segment.start_seconds,
    endSeconds: segment.end_seconds,
    duration: segment.end_seconds - segment.start_seconds,
    originalStart: segment.start_seconds,
    originalEnd: segment.end_seconds,
    frameTime: frameTime,
    minTime: Math.max(0, frameTime - 15), // Show 15s before frame
    maxTime: frameTime + 15, // Show 15s after frame
    visualLeft: 0,
    visualWidth: 100
  };
  
  calculateVisualPosition();
}

function calculateVisualPosition() {
  const { startSeconds, endSeconds, minTime, maxTime } = kisAdjustment.value;
  const totalRange = maxTime - minTime;
  
  kisAdjustment.value.visualLeft = ((startSeconds - minTime) / totalRange) * 100;
  kisAdjustment.value.visualWidth = ((endSeconds - startSeconds) / totalRange) * 100;
}

function adjustKisWindow(deltaSeconds) {
  // Expand or shrink window symmetrically
  const halfDelta = deltaSeconds / 2;
  
  let newStart = kisAdjustment.value.startSeconds - halfDelta;
  let newEnd = kisAdjustment.value.endSeconds + halfDelta;
  
  // Ensure minimum 1 second duration
  if (newEnd - newStart < 1) {
    return;
  }
  
  // Ensure start >= 0
  if (newStart < 0) {
    newStart = 0;
  }
  
  kisAdjustment.value.startSeconds = newStart;
  kisAdjustment.value.endSeconds = newEnd;
  
  updateKisSegment();
}

function shiftKisWindow(seconds) {
  // Shift the entire window by 'seconds' (negative = backward/left, positive = forward/right)
  let newStart = kisAdjustment.value.startSeconds + seconds;
  let newEnd = kisAdjustment.value.endSeconds + seconds;
  
  const { minTime, maxTime, duration } = kisAdjustment.value;
  
  // Clamp to boundaries
  if (newStart < 0) {
    newStart = 0;
    newEnd = newStart + duration;
  }
  
  kisAdjustment.value.startSeconds = newStart;
  kisAdjustment.value.endSeconds = newEnd;
  
  updateKisSegment();
}

function updateKisSegment() {
  // Round to 1 decimal place to prevent floating point precision issues
  kisAdjustment.value.startSeconds = Math.round(kisAdjustment.value.startSeconds * 10) / 10;
  kisAdjustment.value.endSeconds = Math.round(kisAdjustment.value.endSeconds * 10) / 10;
  
  // Recalculate duration
  kisAdjustment.value.duration = kisAdjustment.value.endSeconds - kisAdjustment.value.startSeconds;
  
  // Update visual position
  calculateVisualPosition();
  
  // Update the actual kis_segment in previewFrame
  if (previewFrame.value && previewFrame.value.entity.kis_segment) {
    previewFrame.value.entity.kis_segment.start_seconds = kisAdjustment.value.startSeconds;
    previewFrame.value.entity.kis_segment.end_seconds = kisAdjustment.value.endSeconds;
    previewFrame.value.entity.kis_segment.start_ms = Math.round(kisAdjustment.value.startSeconds * 1000);
    previewFrame.value.entity.kis_segment.end_ms = Math.round(kisAdjustment.value.endSeconds * 1000);
  }
}

function resetKisSegment() {
  const frameTime = kisAdjustment.value.frameTime;
  const window = 2.5; // New default (5s total)
  kisAdjustment.value.startSeconds = Math.max(0, frameTime - window);
  kisAdjustment.value.endSeconds = frameTime + window;
  updateKisSegment();
}

// Drag handlers for timeline interaction
function handleTimelineClick(e) {
  // Click on empty timeline area - jump to that position
  if (!dragState.value.isDragging && e.target === timelineContainer.value) {
    const containerRect = timelineContainer.value.getBoundingClientRect();
    const clickX = e.clientX - containerRect.left;
    const clickPercent = (clickX / containerRect.width) * 100;
    
    // Convert to time
    const { minTime, maxTime, duration } = kisAdjustment.value;
    const totalRange = maxTime - minTime;
    const clickTime = minTime + (clickPercent / 100) * totalRange;
    
    // Center segment on click position
    const halfDuration = duration / 2;
    kisAdjustment.value.startSeconds = Math.max(0, clickTime - halfDuration);
    kisAdjustment.value.endSeconds = clickTime + halfDuration;
    
    updateKisSegment();
  }
}

function handleSegmentDragStart(e) {
  dragState.value.isDragging = true;
  dragState.value.dragType = 'move';
  dragState.value.startX = e.clientX;
  dragState.value.startLeft = kisAdjustment.value.visualLeft;
  
  document.addEventListener('mousemove', handleDragMove);
  document.addEventListener('mouseup', handleDragEnd);
  e.preventDefault();
}

function handleLeftEdgeDragStart(e) {
  dragState.value.isDragging = true;
  dragState.value.dragType = 'resize-left';
  dragState.value.startX = e.clientX;
  dragState.value.startLeft = kisAdjustment.value.visualLeft;
  dragState.value.startWidth = kisAdjustment.value.visualWidth;
  
  document.addEventListener('mousemove', handleDragMove);
  document.addEventListener('mouseup', handleDragEnd);
  e.preventDefault();
}

function handleRightEdgeDragStart(e) {
  dragState.value.isDragging = true;
  dragState.value.dragType = 'resize-right';
  dragState.value.startX = e.clientX;
  dragState.value.startLeft = kisAdjustment.value.visualLeft;
  dragState.value.startWidth = kisAdjustment.value.visualWidth;
  
  document.addEventListener('mousemove', handleDragMove);
  document.addEventListener('mouseup', handleDragEnd);
  e.preventDefault();
}

function handleDragMove(e) {
  if (!dragState.value.isDragging || !timelineContainer.value) return;
  
  const containerRect = timelineContainer.value.getBoundingClientRect();
  const deltaX = e.clientX - dragState.value.startX;
  const deltaPercent = (deltaX / containerRect.width) * 100;
  
  const { minTime, maxTime } = kisAdjustment.value;
  const totalRange = maxTime - minTime;
  const deltaTime = (deltaPercent / 100) * totalRange;
  
  if (dragState.value.dragType === 'move') {
    // Move entire segment
    const duration = kisAdjustment.value.endSeconds - kisAdjustment.value.startSeconds;
    let newStart = kisAdjustment.value.startSeconds + deltaTime;
    let newEnd = newStart + duration;
    
    // Clamp to boundaries
    if (newStart < minTime) {
      newStart = minTime;
      newEnd = newStart + duration;
    }
    if (newEnd > maxTime) {
      newEnd = maxTime;
      newStart = newEnd - duration;
    }
    
    kisAdjustment.value.startSeconds = Math.max(0, newStart);
    kisAdjustment.value.endSeconds = newEnd;
    
    // Reset for next move
    dragState.value.startX = e.clientX;
    
  } else if (dragState.value.dragType === 'resize-left') {
    // Resize from left edge
    let newStart = kisAdjustment.value.startSeconds + deltaTime;
    
    // Ensure minimum 1s duration
    if (kisAdjustment.value.endSeconds - newStart < 1) {
      newStart = kisAdjustment.value.endSeconds - 1;
    }
    
    // Clamp to boundaries
    if (newStart < minTime) newStart = minTime;
    if (newStart < 0) newStart = 0;
    
    kisAdjustment.value.startSeconds = newStart;
    
    // Reset for next move
    dragState.value.startX = e.clientX;
    
  } else if (dragState.value.dragType === 'resize-right') {
    // Resize from right edge
    let newEnd = kisAdjustment.value.endSeconds + deltaTime;
    
    // Ensure minimum 1s duration
    if (newEnd - kisAdjustment.value.startSeconds < 1) {
      newEnd = kisAdjustment.value.startSeconds + 1;
    }
    
    // Clamp to boundaries
    if (newEnd > maxTime) newEnd = maxTime;
    
    kisAdjustment.value.endSeconds = newEnd;
    
    // Reset for next move
    dragState.value.startX = e.clientX;
  }
  
  updateKisSegment();
}

function handleDragEnd() {
  dragState.value.isDragging = false;
  dragState.value.dragType = null;
  
  document.removeEventListener('mousemove', handleDragMove);
  document.removeEventListener('mouseup', handleDragEnd);
}

function getPlaceholder() {
  if (mode.value === 'temporal') return 'First scene query (what happens first)...';
  return 'Enter search query...';
}

function canSearch() {
  if (mode.value === 'ocr') return ocrQuery.value.trim();
  if (mode.value === 'temporal') {
    // At least 2 queries with content
    const filledQueries = temporalQueries.value.filter(q => q.trim());
    return filledQueries.length >= 2;
  }
  return query.value.trim();
}


function addTemporalQuery() {
  temporalQueries.value.push('');
}

function removeTemporalQuery(index) {
  if (temporalQueries.value.length > 2) {
    temporalQueries.value.splice(index, 1);
  }
}

async function handleSearch() {
  loading.value = true;
  error.value = '';
  results.value = [];
  selectedFrames.value = [];
  
  try {
    let res;
    
    if (mode.value === 'temporal') {
      const queries = temporalQueries.value.filter(q => q.trim());
      const gapConstraints = []; // Add logic for time gap constraints if needed
      
      res = await fetch('/SequentialQuery', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          queries: queries,
          top_k: topK.value,
          time_gap_constraints: gapConstraints
        })
      });
      
      // Add combined query to history for reference
      addToHistory(queries.join(' | ')); // Use pipe as visual separator
      
    } else if (mode.value === 'ocr') {
      const body = { 
        First_query: '',
        Next_query: '',
        ocr_text: ocrQuery.value,
        top_k: topK.value
      };
      
      res = await fetch('/TextQuery', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      });
      
    } else {
      // Standard text search
      const body = { 
        First_query: query.value,
        Next_query: '',
        top_k: topK.value
      };
      
      res = await fetch('/TextQuery', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body)
      });
    }
    
    // Validate response before parsing
    if (!res) {
      throw new Error('No response received');
    }
    
    // Add to history
    if (mode.value === 'standard') {
      addToHistory(query.value);
    } else if (mode.value === 'ocr') {
      addToHistory(ocrQuery.value);
    }
    
    // Check if response has content
    const contentType = res.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      const text = await res.text();
      throw new Error(`Expected JSON response, got: ${contentType}. Response: ${text.substring(0, 200)}`);
    }
    
    const data = await res.json();
    
    if (res.ok) {
      results.value = data.kq || data.results || [];
    } else {
      error.value = data.detail || 'Search failed';
    }
    
  } catch (e) {
    error.value = e.message;
  } finally {
    loading.value = false;
  }
}

function isSelected(frame) {
  return selectedFrames.value.some(f => 
    f.entity.frame_id === frame.entity.frame_id && 
    f.entity.video === frame.entity.video
  );
}

function toggleSelection(frame) {
  if (isSelected(frame)) {
    selectedFrames.value = selectedFrames.value.filter(f => 
      !(f.entity.frame_id === frame.entity.frame_id && f.entity.video === frame.entity.video)
    );
  } else {
    selectedFrames.value.push(frame);
  }
}

function openPreview(frame) {
  previewFrame.value = frame;
  loadNeighborFrames(frame);
  initKisAdjustment(frame); // Initialize KIS adjustment controls
}

async function loadNeighborFrames(frame) {
  neighborFrames.value = [];
  
  try {
    const currentVideo = frame.entity.video;
    const currentFrameId = frame.entity.frame_id;
    const currentKeyframePath = frame.entity.keyframe_path;
    
    // Fetch neighbor frames from API
    const res = await fetch('/get_neighbor_frames', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        video: currentVideo,
        frame_id: currentFrameId,
        keyframe_path: currentKeyframePath,  // Pass path for batch folder hint
        count: 3,  // Get 3 before and 3 after
        stride: 25 // Gap of 25 frames (approx 1s) to improve diversity
      })
    });
    
    if (!res.ok) {
      console.error('Failed to fetch neighbor frames:', res.statusText);
      return;
    }
    
    const data = await res.json();
    const neighbors = data.neighbors || [];
    
    neighborFrames.value = neighbors.map(n => {
      // Padded time calculation for true time display
      let ts = 0;
      if (n.time && typeof n.time === 'string') {
        const p = n.time.split(':');
        if (p.length === 3) ts = parseInt(p[0])*3600 + parseInt(p[1])*60 + parseFloat(p[2]);
        else if (p.length === 2) ts = parseInt(p[0])*60 + parseFloat(p[1]);
      }
      return {
        path: n.keyframe_path,
        offset: n.offset,
        frame: {
          distance: 0.0,
          entity: {
            video: n.video,
            frame_id: n.frame_id,
            keyframe_path: n.keyframe_path,
            time: n.time,
            time_seconds: ts
          }
        }
      };
    });
    
    console.log(`Loaded ${neighborFrames.value.length} neighbor frames from API: ${neighborFrames.value.filter(n => n.offset < 0).length} before, ${neighborFrames.value.filter(n => n.offset > 0).length} after`);
    
  } catch (e) {
    console.error('Failed to load neighbor frames:', e);
  }
}

function closePreview() {
  if (videoPlayer.value) {
    videoPlayer.value.pause();
  }
  previewFrame.value = null;
}

function seekToFrameTime() {
  if (!videoPlayer.value || !previewFrame.value || !previewFrame.value.entity) return;
  
  try {
    let seconds = 0;
    const entity = previewFrame.value.entity;

    // Debug logging for seek diagnosis
    console.log('SeekToFrameTime Input:', { 
      time_seconds: entity.time_seconds, 
      type_ts: typeof entity.time_seconds,
      time: entity.time, 
      frame_id: entity.frame_id, 
      video: entity.video 
    });

    // Prefer pre-calculated seconds (handle both number and numeric string)
    if (entity.time_seconds !== undefined && entity.time_seconds !== null && !isNaN(parseFloat(entity.time_seconds)) && parseFloat(entity.time_seconds) > 0) {
      seconds = parseFloat(entity.time_seconds);
      console.log('Using backend time_seconds:', seconds);
    } else if (entity.time && typeof entity.time === 'string' && entity.time.includes(':')) {
      // Parse time string (format: HH:MM:SS or MM:SS)
      const timeStr = String(entity.time);
      const timeParts = timeStr.split(':');
      
      if (timeParts.length === 3) {
        // HH:MM:SS
        seconds = parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2]);
      } else if (timeParts.length === 2) {
        // MM:SS
        seconds = parseInt(timeParts[0]) * 60 + parseFloat(timeParts[1]);
      }
      console.log('Parsed time string:', seconds);
    } else if (entity.frame_id) {
       // FINAL FALLBACK: Calculate from frame_id
       // Determine FPS from backend provided property or fallback to 25.0
       let fps = parseFloat(entity.fps) || 25.0;
       seconds = parseFloat(entity.frame_id) / fps;
       console.log('Seek fallback used frame_id:', entity.frame_id, 'with FPS:', fps, '->', seconds);
    }
    
    // Seek to the timestamp
    if (Number.isFinite(seconds) && videoPlayer.value) {
      console.log('Executing seek to:', seconds, 'Current Player Time:', videoPlayer.value.currentTime);
      // Small buffer to ensure we land on the frame (sometimes browsers are picky)
      videoPlayer.value.currentTime = Math.max(0, seconds);
    }
  } catch (e) {
    console.error('Failed to seek video:', e);
  }
}

function skipBackward() {
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = Math.max(0, videoPlayer.value.currentTime - 2);
  }
}

function skipForward() {
  if (videoPlayer.value) {
    videoPlayer.value.currentTime = Math.min(
      videoPlayer.value.duration, 
      videoPlayer.value.currentTime + 2
    );
  }
}

function getVideoPath(frame) {
  if (!frame || !frame.entity) return '';
  
  // 1. Prefer explicit video_path from backend
  if (frame.entity.video_path) {
    return `/videos/${frame.entity.video_path}`;
  }
  
  // 2. Fallback to constructing from video ID
  const video = frame.entity.video;
  if (!video) return '';
  
  // If video is just V001 (old format), we might need L01_ prefix, 
  // but backend should now provide normalized video or video_path
  return `/videos/${video}${video.endsWith('.mp4') ? '' : '.mp4'}`;
}

async function loginDRES() {
  loggingIn.value = true;
  loginError.value = '';
  
  try {
    let baseUrl = dresBaseUrl.value || 'https://eventretrieval.one';
    // Remove trailing slash if present
    if (baseUrl.endsWith('/')) baseUrl = baseUrl.slice(0, -1);
    
    const loginUrl = `${baseUrl}/api/v2/login`;
    console.log('🔐 DRES Login: Authenticating at', loginUrl);
    
    // Step 1: Login to get session ID
    const loginRes = await fetch(loginUrl, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        username: dresLogin.value.username,
        password: dresLogin.value.password
      })
    });
    
    if (!loginRes.ok) {
      const error = await loginRes.json().catch(() => ({ message: 'Login failed' }));
      throw new Error(error.message || `HTTP ${loginRes.status}`);
    }
    
    const loginData = await loginRes.json();
    const sessionId = loginData.sessionId;
    
    if (!sessionId) {
      throw new Error('No session ID received from server');
    }
    
    console.log('✅ Session ID received:', sessionId.substring(0, 8) + '...');
    
    // Step 2: Get evaluation list
    console.log('📋 Fetching evaluation list...');
    const evalRes = await fetch(`${baseUrl}/api/v2/client/evaluation/list?session=${sessionId}`);
    
    if (!evalRes.ok) {
      throw new Error(`Failed to get evaluations: HTTP ${evalRes.status}`);
    }
    
    const evaluations = await evalRes.json();
    console.log(`Found ${evaluations.length} evaluations:`, evaluations.map(e => `${e.name} (${e.status})`));
    
    // Try to find ACTIVE evaluation first, fallback to CREATED
    let selectedEval = evaluations.find(e => e.status === 'ACTIVE');
    if (!selectedEval) {
      selectedEval = evaluations.find(e => e.status === 'CREATED');
    }
    
    if (!selectedEval && evaluations.length > 0) {
      // Use first available evaluation
      selectedEval = evaluations[0];
      console.warn('⚠️ No ACTIVE/CREATED evaluation, using first:', selectedEval.name);
    }
    
    if (!selectedEval) {
      throw new Error('No evaluations available');
    }
    
    console.log('✅ Selected evaluation:', selectedEval.name, '(', selectedEval.id, ')');
    
    // Save to localStorage and state
    localStorage.setItem('contestSessionID', sessionId);
    localStorage.setItem('evaluationID', selectedEval.id);
    localStorage.setItem('dresUsername', dresLogin.value.username);
    localStorage.setItem('dresBaseUrl', baseUrl);
    
    dresSession.value.sessionId = sessionId;
    dresSession.value.evaluationId = selectedEval.id;
    dresSession.value.evaluationName = selectedEval.name;
    dresSession.value.username = dresLogin.value.username;
    dresConnected.value = true;
    
    console.log('🎉 DRES login successful!');
    
    showLoginModal.value = false;
    dresLogin.value.password = ''; // Clear password
    
  } catch (e) {
    console.error('❌ DRES login failed:', e);
    loginError.value = e.message;
  } finally {
    loggingIn.value = false;
  }
}

function logoutDRES() {
  localStorage.removeItem('contestSessionID');
  localStorage.removeItem('evaluationID');
  localStorage.removeItem('dresUsername');
  // Keep dresBaseUrl so user doesn't have to re-type it
  
  dresSession.value = {
    sessionId: '',
    evaluationId: '',
    evaluationName: '',
    username: ''
  };
  dresConnected.value = false;
  loginError.value = 'Logged out. Please login again to refresh evaluation list.';
  console.log('🚪 DRES Logged out');
}

function copyDRESJson() {
  try {
    let body;
    
    if (dresConfig.value.taskType === 'qa') {
      // QA Format: "ANSWER-VIDEO_ID-TIME(ms)"
      const firstFrame = selectedFrames.value[0];
      if (!firstFrame) {
        alert('No frames selected!');
        return;
      }
      
      // Extract video ID (L##_V###) - use video field directly
      const videoId = firstFrame.entity.video;
      
      // Calculate time in milliseconds
      // Calculate time in milliseconds (robust)
      let timeMs = 0;
      if (typeof firstFrame.entity.time_seconds === 'number' && firstFrame.entity.time_seconds > 0) {
        timeMs = Math.floor(firstFrame.entity.time_seconds * 1000);
      } else if (firstFrame.entity.time && typeof firstFrame.entity.time === 'string' && firstFrame.entity.time.includes(':')) {
        const timeParts = firstFrame.entity.time.split(':');
        if (timeParts.length === 3) {
          timeMs = Math.floor((parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000);
        }
      } else if (firstFrame.entity.frame_id) {
         let fps = parseFloat(firstFrame.entity.fps) || 25.0;
         timeMs = Math.floor((parseFloat(firstFrame.entity.frame_id) / fps) * 1000);
      }
      
      const answerText = `${dresConfig.value.answerText}-${videoId}-${timeMs}`;
      
      body = {
        answerSets: [{
          answers: [{
            text: answerText
          }]
        }]
      };
    } else {
      // KIS Format
      body = {
        answerSets: [{
          answers: selectedFrames.value.map(f => {
            // Extract batch and video - use video field directly
            const mediaItemName = f.entity.video;
            
            // Use pre-calculated KIS segment if available
            if (f.entity.kis_segment) {
              return {
                mediaItemName,
                start: f.entity.kis_segment.start_ms,
                end: f.entity.kis_segment.end_ms
              };
            }
            
            // Fallback: calculate manually
            // Fallback: calculate manually
            let centerMs = 0;
            if (typeof f.entity.time_seconds === 'number' && f.entity.time_seconds > 0) {
                 centerMs = Math.floor(f.entity.time_seconds * 1000);
            } else if (f.entity.time && typeof f.entity.time === 'string' && f.entity.time.includes(':')) {
                 const timeParts = f.entity.time.split(':');
                 if (timeParts.length === 3) {
                   centerMs = (parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000;
                 }
            } else if (f.entity.frame_id) {
                 centerMs = Math.floor((parseFloat(f.entity.frame_id) / 25.0) * 1000);
            }
            
            const windowMs = (dresConfig.value.kisWindow || 0.5) * 1000; 
            return {
              mediaItemName,
              start: Math.max(0, Math.floor(centerMs - windowMs)),
              end: Math.floor(centerMs + windowMs)
            };
          })
        }]
      };
    }
    
    const jsonStr = JSON.stringify(body, null, 2);
    
    // Copy to clipboard
    navigator.clipboard.writeText(jsonStr).then(() => {
      submitResult.value = {
        success: true,
        message: '✅ JSON copied to clipboard!'
      };
      
      console.log('📋 DRES JSON copied:');
      console.log(jsonStr);
      
      setTimeout(() => {
        submitResult.value = null;
      }, 3000);
    }).catch(err => {
      console.error('Copy failed:', err);
      alert('Failed to copy. See console for JSON.');
      console.log(jsonStr);
    });
    
  } catch (e) {
    console.error('Error generating JSON:', e);
    alert('Error: ' + e.message);
  }
}


async function submitToDRES() {
  if (!dresConnected.value || !dresSession.value.sessionId || !dresSession.value.evaluationId) {
    submitResult.value = {
      success: false,
      message: 'Please login to DRES first'
    };
    return;
  }
  
  submitting.value = true;
  submitResult.value = null;
  
  try {
    let body;
    
    if (dresConfig.value.taskType === 'qa') {
      // QA format: text answer
      body = {
        answerSets: [{
          answers: [{
            text: dresConfig.value.answerText
          }]
        }]
      };
    } else {
      // KIS format: video + timestamp segment
      body = {
        answerSets: [{
          answers: selectedFrames.value.map(f => {
            // Extract batch and video - use video field directly
            const mediaItemName = f.entity.video;
            
            console.log('📤 Submitting frame:', {
              video: f.entity.video,
              mediaItemName,
              keyframe_path: f.entity.keyframe_path
            });
            
            // Use pre-calculated KIS segment if available
            if (f.entity.kis_segment) {
              return {
                mediaItemName,
                start: f.entity.kis_segment.start_ms,
                end: f.entity.kis_segment.end_ms
              };
            }
            
            // Fallback: calculate manually (6 second window)
            let centerMs = 0;
            if (typeof f.entity.time_seconds === 'number' && f.entity.time_seconds > 0) {
              centerMs = Math.floor(f.entity.time_seconds * 1000);
            } else if (f.entity.time && typeof f.entity.time === 'string' && f.entity.time.includes(':')) {
              const timeParts = f.entity.time.split(':');
              if (timeParts.length === 3) {
                centerMs = (parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000;
              }
            } else if (f.entity.frame_id) {
              centerMs = Math.floor((parseFloat(f.entity.frame_id) / 25.0) * 1000);
            }
            
            const windowMs = (dresConfig.value.kisWindow || 0.5) * 1000; 
            return {
              mediaItemName,
              start: Math.max(0, Math.floor(centerMs - windowMs)),
              end: Math.floor(centerMs + windowMs)
            };
          })
        }]
      };
    }
    
    const baseUrl = dresBaseUrl.value || 'https://eventretrieval.one';
    
    const res = await fetch(`${baseUrl}/api/v2/submit/${dresSession.value.evaluationId}?session=${dresSession.value.sessionId}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    
    const data = await res.json().catch(() => null);
    
    if (!res.ok) {
      const errorMsg = data?.description || data?.message || `HTTP ${res.status}`;
      throw new Error(errorMsg);
    }
    
    // Check DRES response status
    const isCorrect = data?.submission === 'CORRECT';
    const description = data?.description || 'Submitted';
    
    submitResult.value = {
      success: true,
      message: isCorrect ? `✅ ${description}` : `⚠️ ${description}`
    };
    
    console.log('📤 DRES Response:', data);
    
    setTimeout(() => {
      showSubmitModal.value = false;
      selectedFrames.value = [];
      submitResult.value = null;
    }, 2000);
    
  } catch (e) {
    submitResult.value = {
      success: false,
      message: e.message
    };
  } finally {
    submitting.value = false;
  }
}

// Submit single frame from preview modal
function copySingleFrameJson() {
  if (!previewFrame.value) {
    alert('No frame selected!');
    return;
  }
  
  try {
    const frame = previewFrame.value;
    let body;
    
    // Get task type from dropdown (kis or qa)
    const taskType = document.querySelector('#preview-modal select')?.value || 'kis';
    
    if (taskType === 'qa') {
      // QA Format
      const answerInput = document.querySelector('.vqa-input-preview');
      const answer = answerInput ? answerInput.value : '';
      
      if (!answer) {
        alert('Please enter an answer for QA submission!');
        return;
      }
      
      // Extract video ID (L##_V###) - use video field directly
      const videoId = frame.entity.video;
      
      // Calculate time in milliseconds
      // Calculate time in milliseconds
      let timeMs = 0;
      if (typeof frame.entity.time_seconds === 'number' && frame.entity.time_seconds > 0) {
        timeMs = Math.floor(frame.entity.time_seconds * 1000);
      } else if (frame.entity.time && typeof frame.entity.time === 'string' && frame.entity.time.includes(':')) {
        const timeParts = frame.entity.time.split(':');
        if (timeParts.length === 3) {
          timeMs = Math.floor((parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000);
        }
      } else if (frame.entity.frame_id) {
        timeMs = Math.floor((parseFloat(frame.entity.frame_id) / 25.0) * 1000);
      }
      
      const answerText = `${answer}-${videoId}-${timeMs}`;
      
      body = {
        answerSets: [{
          answers: [{
            text: answerText
          }]
        }]
      };
    } else {
      // Extract video ID (L##_V###) - use video field directly
      const mediaItemName = frame.entity.video;
      
      let start_ms, end_ms;
      
      if (frame.entity.kis_segment) {
        start_ms = frame.entity.kis_segment.start_ms;
        end_ms = frame.entity.kis_segment.end_ms;
      } else {
      // Fallback
        let centerMs = 0;
        if (typeof frame.entity.time_seconds === 'number' && frame.entity.time_seconds > 0) {
          centerMs = Math.floor(frame.entity.time_seconds * 1000);
        } else if (frame.entity.time && typeof frame.entity.time === 'string' && frame.entity.time.includes(':')) {
          const timeParts = frame.entity.time.split(':');
          if (timeParts.length === 3) {
            centerMs = (parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000;
          }
        } else if (frame.entity.frame_id) {
          centerMs = Math.floor((parseFloat(frame.entity.frame_id) / 25.0) * 1000);
        }
        const windowMs = 3000;
        start_ms = Math.max(0, Math.floor(centerMs - windowMs));
        end_ms = Math.floor(centerMs + windowMs);
      }
      
      body = {
        answerSets: [{
          answers: [{
            mediaItemName,
            start: start_ms,
            end: end_ms
          }]
        }]
      };
    }
    
    const jsonStr = JSON.stringify(body, null, 2);
    
    // Copy to clipboard
    navigator.clipboard.writeText(jsonStr).then(() => {
      previewSubmitResult.value = {
        success: true,
        message: '✅ JSON copied to clipboard!'
      };
      
      console.log('📋 DRES JSON (Single Frame):');
      console.log(jsonStr);
      
      setTimeout(() => {
        previewSubmitResult.value = null;
      }, 3000);
    }).catch(err => {
      console.error('Copy failed:', err);
      alert('Failed to copy. See console for JSON.');
      console.log(jsonStr);
    });
    
  } catch (e) {
    console.error('Error generating JSON:', e);
    alert('Error: ' + e.message);
  }
}

async function submitSingleFrame() {
  if (!dresConnected.value || !dresSession.value.sessionId || !dresSession.value.evaluationId) {
    previewSubmitResult.value = {
      success: false,
      message: 'Please login to DRES first'
    };
    return;
  }
  
  if (!previewFrame.value) {
    previewSubmitResult.value = {
      success: false,
      message: 'No frame selected'
    };
    return;
  }
  
  submitting.value = true;
  previewSubmitResult.value = null;
  
  try {
    let body;
    const frame = previewFrame.value;
    
    if (previewSubmitConfig.value.taskType === 'qa') {
      // QA format: "<ANSWER>-<VIDEO_ID>-<TIME(ms)>"
      const videoId = frame.entity.video;
      
      // Calculate center time in ms
      let centerMs = 0;
      if (typeof frame.entity.time_seconds === 'number' && frame.entity.time_seconds > 0) {
        centerMs = Math.floor(frame.entity.time_seconds * 1000);
      } else if (frame.entity.time && typeof frame.entity.time === 'string' && frame.entity.time.includes(':')) {
        const timeParts = frame.entity.time.split(':');
        if (timeParts.length === 3) {
          centerMs = Math.floor((parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000);
        }
      } else if (frame.entity.frame_id) {
        centerMs = Math.floor((parseFloat(frame.entity.frame_id) / 25.0) * 1000);
      }
      
      const answerText = previewSubmitConfig.value.answerText || '';
      const combinedAnswer = `${answerText}-${videoId}-${centerMs}`;
      
      body = {
        session: dresSession.value.sessionId,
        answerSets: [{
          answers: [{
            text: combinedAnswer
          }]
        }]
      };
    } else {
      // KIS format: video segment with start/end ms
      let startMs, endMs;
      
      // Use adjusted KIS segment if available
      if (frame.entity.kis_segment) {
        startMs = frame.entity.kis_segment.start_ms;
        endMs = frame.entity.kis_segment.end_ms;
      } else {
        // Fallback: calculate 3s window
        let centerMs = 0;
        if (typeof frame.entity.time_seconds === 'number' && frame.entity.time_seconds > 0) {
          centerMs = Math.floor(frame.entity.time_seconds * 1000);
        } else if (frame.entity.time && typeof frame.entity.time === 'string' && frame.entity.time.includes(':')) {
          const timeParts = frame.entity.time.split(':');
          if (timeParts.length === 3) {
            centerMs = (parseInt(timeParts[0]) * 3600 + parseInt(timeParts[1]) * 60 + parseFloat(timeParts[2])) * 1000;
          }
        } else if (frame.entity.frame_id) {
          centerMs = Math.floor((parseFloat(frame.entity.frame_id) / 25.0) * 1000);
        }
        
        const windowMs = (previewSubmitConfig.value.kisWindow || 0.5) * 1000;
        startMs = Math.max(0, Math.floor(centerMs - windowMs));
        endMs = Math.floor(centerMs + windowMs);
      }
      
      // Extract proper video ID - use video field directly
      const mediaItemName = frame.entity.video;
      
      body = {
        answerSets: [{
          answers: [{
            mediaItemName,
            start: startMs,
            end: endMs
          }]
        }]
      };
    }
    
    const baseUrl = dresBaseUrl.value || 'https://eventretrieval.one';
    
    const res = await fetch(`${baseUrl}/api/v2/submit/${dresSession.value.evaluationId}?session=${dresSession.value.sessionId}`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    
    const data = await res.json().catch(() => null);
    
    if (!res.ok) {
      const errorMsg = data?.description || data?.message || `HTTP ${res.status}`;
      throw new Error(errorMsg);
    }
    
    // Check DRES response
    const isCorrect = data?.submission === 'CORRECT';
    const description = data?.description || 'Submitted';
    
    previewSubmitResult.value = {
      success: true,
      message: isCorrect ? `✅ ${description}` : `⚠️ ${description}`
    };
    
    console.log('📤 DRES Response (Single):', data);
    
    // Clear result after 3s
    setTimeout(() => {
      previewSubmitResult.value = null;
    }, 3000);
    
  } catch (e) {
    previewSubmitResult.value = {
      success: false,
      message: e.message
    };
  } finally {
    submitting.value = false;
  }
}

// Restore DRES session from localStorage on mount
onMounted(() => {
  const sessionId = localStorage.getItem('contestSessionID');
  const evaluationId = localStorage.getItem('evaluationID');
  const username = localStorage.getItem('dresUsername');
  const baseUrl = localStorage.getItem('dresBaseUrl');
  
  if (sessionId && evaluationId) {
    console.log('🔄 Restoring DRES session from localStorage...');
    dresSession.value.sessionId = sessionId;
    dresSession.value.evaluationId = evaluationId;
    dresSession.value.username = username || 'Unknown';
    dresConnected.value = true;
    
    if (baseUrl) {
      dresBaseUrl.value = baseUrl;
    }
    
    console.log('✅ DRES session restored:', {
      username: dresSession.value.username,
      evaluationId: evaluationId.substring(0, 8) + '...'
    });
  } else {
    console.log('ℹ️ No DRES session found in localStorage');
  }
});

</script>
