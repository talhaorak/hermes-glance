import SwiftUI
import AppKit
import GlanceCore

// Warm paper with restrained sage/amber signals; status owns the color, not the whole row.
enum Palette {
    static let paper = Color(red: 0.965, green: 0.961, blue: 0.933)
    static let card = Color(red: 0.997, green: 0.993, blue: 0.977)
    static let ink = Color(red: 0.19, green: 0.25, blue: 0.21)
    static let muted = Color(red: 0.43, green: 0.47, blue: 0.43)
    static let sage = Color(red: 0.28, green: 0.43, blue: 0.32)
    static let amber = Color(red: 0.61, green: 0.38, blue: 0.10)
    static let line = Color(red: 0.85, green: 0.87, blue: 0.82)
}

struct GlanceView: View {
    @ObservedObject var store: BridgeStore
    @ObservedObject var window: WindowController
    @State private var filter = SessionFilter.active
    @State private var noticeExpanded = false
    private var sessions: [GlanceSession] { filter.apply(store.snapshot.sessions) }
    private var running: Int { store.snapshot.sessions.filter { $0.status == .running }.count }
    private var waiting: Int { store.snapshot.sessions.filter { $0.status == .waiting }.count }
    var body: some View {
        VStack(spacing: 0) {
            header.frame(height: GlanceLayout.headerHeight)
            HStack(spacing: 4) {
                ForEach(SessionFilter.allCases, id: \.self) { item in
                    Button { filter = item } label: {
                        Text(item.rawValue).font(.system(size: 11, weight: filter == item ? .semibold : .regular))
                            .padding(.horizontal, 9).frame(height: 20)
                            .background(filter == item ? Palette.card : .clear, in: RoundedRectangle(cornerRadius: 5))
                    }.buttonStyle(.plain).accessibilityAddTraits(filter == item ? .isSelected : [])
                }
                Spacer(minLength: 0)
                if !store.presentation.completedIDs.isEmpty {
                    Text("✓ \(store.presentation.completedIDs.count) tamamlandı")
                        .font(.system(size: 10)).foregroundStyle(Palette.sage)
                        .help("Az önce çalışırken tamamlandığı gözlenen oturumlar")
                }
                Text("\(sessions.count)").font(.system(size: 10).monospacedDigit()).foregroundStyle(Palette.muted)
            }.padding(.horizontal, 10).frame(height: GlanceLayout.filterHeight)
            Rectangle().fill(Palette.line).frame(height: 1)
            ScrollView {
                LazyVStack(spacing: GlanceLayout.rowSpacing) {
                    if !store.snapshot.connected || store.snapshot.error != nil { connectionNotice }
                    if sessions.isEmpty { emptyState }
                    ForEach(sessions) { session in
                        SessionCard(session: session,
                                    expanded: store.presentation.expandedIDs.contains(session.id),
                                    recentlyCompleted: store.presentation.completedIDs.contains(session.id)) {
                            store.toggleExpansion(session.id)
                        }
                    }
                }.padding(.horizontal, 8).padding(.vertical, 6)
            }
        }
        // NSHostingView already reserves the native titlebar safe area.
        .frame(minWidth: 360, maxWidth: .infinity, minHeight: 320, maxHeight: .infinity)
        .background(Palette.paper).foregroundStyle(Palette.ink).preferredColorScheme(.light)
    }
    private var header: some View {
        HStack(spacing: 6) {
            Text("Glance").font(.system(size: 13, weight: .semibold, design: .rounded))
            Circle().fill(store.snapshot.connected ? Palette.sage : Palette.amber).frame(width: 5, height: 5)
                .accessibilityLabel(store.snapshot.connected ? "Bağlı" : "Bağlantı yok")
                .help(store.snapshot.connected ? "Yerel gözlemci bağlı · salt okunur" : "Canlı bağlantı yok")
            Spacer(minLength: 0)
            Text("\(running) çalışan").foregroundStyle(Palette.sage)
            Text("·").foregroundStyle(Palette.muted)
            Text("\(waiting) bekleyen").foregroundStyle(waiting > 0 ? Palette.amber : Palette.muted)
            Menu {
                Toggle("Her zaman üstte", isOn: $window.alwaysOnTop)
                Menu("Ekrana taşı") {
                    ForEach(Array(NSScreen.screens.enumerated()), id: \.offset) { index, screen in
                        Button("\(index + 1) · \(screen.localizedName)") { window.move(to: screen) }
                    }
                }
                Button("Yeniden bağlan") { store.start() }
                Divider()
                Button("Gizle") { window.hide() }
                Button("Hermes Glance’tan çık") { NSApp.terminate(nil) }
            } label: {
                Image(systemName: "ellipsis").frame(width: 22, height: 22)
            }.menuStyle(.borderlessButton).menuIndicator(.hidden).fixedSize().help("Pencere ayarları")
        }.font(.system(size: 10)).padding(.horizontal, 12)
    }
    private var connectionNotice: some View {
        VStack(alignment: .leading, spacing: 4) {
            Button { noticeExpanded.toggle() } label: {
                HStack(spacing: 5) {
                    Image(systemName: "exclamationmark.circle")
                    Text(store.snapshot.connected ? "Bağlantı ve kapsam · ≈1 sn" : "Canlı bağlantı yok · durum bilinmiyor").lineLimit(1)
                    Spacer(minLength: 0)
                    Image(systemName: noticeExpanded ? "chevron.up" : "chevron.down")
                }.frame(height: 22).contentShape(Rectangle())
            }.buttonStyle(.plain)
            if noticeExpanded {
                Text(store.snapshot.error ?? "Yerel gözlemci bekleniyor.").textSelection(.enabled)
                Button("Yeniden bağlan") { store.start() }.buttonStyle(.plain).underline()
            }
        }.font(.system(size: 11)).foregroundStyle(Palette.amber).padding(.horizontal, 5)
    }
    private var emptyState: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(store.snapshot.connected ? "\(filter == .waiting ? "Bekleyen" : "Aktif") oturum yok" : "Gözlemci bağlantısı bekleniyor")
            if filter != .all {
                Button("Geçmişi göster · Tümü") { filter = .all }.buttonStyle(.plain).foregroundStyle(Palette.sage)
            }
        }.font(.system(size: 12)).foregroundStyle(Palette.muted).frame(maxWidth: .infinity, alignment: .leading).padding(12)
    }
}

struct SessionCard: View {
    let session: GlanceSession
    let expanded: Bool
    let recentlyCompleted: Bool
    let toggleExpansion: () -> Void
    @State private var openError = false
    private var accent: Color { session.status == .waiting ? Palette.amber : session.status == .running || recentlyCompleted ? Palette.sage : Palette.muted }
    private var statusLabel: String {
        switch session.status {
        case .running: return "Çalışıyor"
        case .waiting: return "Bekliyor"
        case .completed: return recentlyCompleted ? "✓ Bitti" : "Bitti"
        case .idle: return "Boşta"
        case .unknown: return "Bilinmiyor"
        }
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    // Only this sibling button navigates; expansion never opens Hermes.
                    Button {
                        guard let url = session.validatedURL else { return }
                        openError = !NSWorkspace.shared.open(url)
                    } label: {
                        HStack(spacing: 4) {
                            Text(session.title).font(.system(size: 12, weight: .semibold)).lineLimit(1)
                            Image(systemName: "arrow.up.right").font(.system(size: 9))
                        }.frame(maxWidth: .infinity, alignment: .leading).contentShape(Rectangle())
                    }.buttonStyle(.plain).disabled(session.validatedURL == nil).help("Hermes’te aç: \(session.title)")
                    Text(statusLabel).font(.system(size: 9, weight: .medium)).foregroundStyle(accent)
                }.frame(height: 18)
                Text(session.latestActivity.replacingOccurrences(of: "\n", with: " "))
                    .font(.system(size: 11)).foregroundStyle(session.status == .waiting ? Palette.amber : Palette.muted)
                    .lineLimit(1).frame(maxWidth: .infinity, alignment: .leading).help(session.latestActivity)
                HStack(spacing: 5) {
                    Text(session.live ? "Canlı" : "Kayıt").font(.system(size: 9)).foregroundStyle(Palette.muted)
                    Spacer(minLength: 0)
                    Button(expanded ? "Daha az" : "Daha fazla", action: toggleExpansion)
                        .buttonStyle(.plain).font(.system(size: 10, weight: .medium)).foregroundStyle(Palette.sage)
                        .accessibilityLabel("\(session.title): \(expanded ? "Daha az" : "Daha fazla")")
                }.frame(height: 14)
            }.padding(.horizontal, 11).frame(height: GlanceLayout.rowHeight)
            if expanded {
                VStack(alignment: .leading, spacing: 5) {
                    if session.status == .waiting, let reason = session.waitingReason { Text(reason).foregroundStyle(Palette.amber) }
                    if !session.summary.isEmpty { Text(session.summary).foregroundStyle(Palette.ink) }
                    if session.lines.isEmpty { Text("Ek kayıt yok").foregroundStyle(Palette.muted) }
                    ForEach(Array(session.lines.suffix(12).enumerated()), id: \.offset) { _, line in
                        Text(line).font(.system(size: 10, design: .monospaced)).foregroundStyle(Palette.muted)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }.font(.system(size: 11)).textSelection(.enabled).padding(.horizontal, 11).padding(.bottom, 10)
            }
        }.frame(maxWidth: .infinity, alignment: .leading)
            .background(Palette.card, in: RoundedRectangle(cornerRadius: 7))
            .overlay(alignment: .leading) { StatusRail(waiting: session.status == .waiting, accent: accent).padding(.vertical, 9) }
            .overlay(RoundedRectangle(cornerRadius: 7).stroke(Palette.line.opacity(0.6), lineWidth: 0.5))
            .alert("Hermes açılamadı", isPresented: $openError) { Button("Tamam", role: .cancel) {} } message: {
                Text("Oturum bağlantısını kabul eden uygulama bulunamadı. Hermes’in kurulu olduğundan emin olun.")
            }
    }
}

private struct StatusRail: View {
    let waiting: Bool
    let accent: Color
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var pulse = false
    var body: some View {
        RoundedRectangle(cornerRadius: 2).fill(accent).frame(width: 2)
            .opacity(waiting ? (reduceMotion ? 0.8 : pulse ? 0.85 : 0.35) : 0.4)
            .task(id: waiting && !reduceMotion) {
                pulse = false
                guard waiting && !reduceMotion else { return }
                withAnimation(.easeInOut(duration: 2.4).repeatForever(autoreverses: true)) { pulse = true }
            }
            .animation(reduceMotion ? nil : .default, value: reduceMotion)
            .accessibilityHidden(true)
    }
}
