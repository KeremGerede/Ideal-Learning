// src/components/YouTubeEmbed.jsx

function getYouTubeEmbedUrl(url) {
    /**
     * YouTube watch / short link URL'lerini embed URL formatına çevirir.
     *
     * Desteklenen örnekler:
     * - https://www.youtube.com/watch?v=VIDEO_ID
     * - https://youtu.be/VIDEO_ID
     */

    if (!url) {
        return null;
    }

    try {
        const parsedUrl = new URL(url);

        if (parsedUrl.hostname.includes("youtube.com")) {
            const videoId = parsedUrl.searchParams.get("v");

            if (videoId) {
                return `https://www.youtube.com/embed/${videoId}`;
            }
        }

        if (parsedUrl.hostname.includes("youtu.be")) {
            const videoId = parsedUrl.pathname.replace("/", "");

            if (videoId) {
                return `https://www.youtube.com/embed/${videoId}`;
            }
        }

        return null;
    } catch {
        return null;
    }
}

function YouTubeEmbed({ url, title }) {
    /**
     * YouTube linki varsa küçük bir embed player gösterir.
     * Link YouTube değilse hiçbir şey render etmez.
     */

    const embedUrl = getYouTubeEmbedUrl(url);

    if (!embedUrl) {
        return null;
    }

    return (
        <div className="mt-4 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
            <iframe
                src={embedUrl}
                title={title || "YouTube video"}
                className="aspect-video w-full"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
            />
        </div>
    );
}

export default YouTubeEmbed;